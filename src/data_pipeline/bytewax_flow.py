#!/usr/bin/env python3
import os
import ssl
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from bytewax import operators as op
from bytewax.connectors.kafka import KafkaSource, KafkaSink
from bytewax.dataflow import Dataflow
from bytewax.run import cli_main

from src.utils.logger_config import setup_logging
from src.configg import (
    KAFKA_BROKER, KAFKA_TOPIC, CONSUMER_GROUP,
    SSL_CAFILE, SSL_CERTFILE, SSL_KEYFILE,
)
from .operators import (
    DatabaseConnections,
    enrich_with_nearest_shop,
    check_proximity_and_generate_message,
    write_to_clickhouse
)

logger = logging.getLogger(__name__)
setup_logging()

# Configurazione SSL per Kafka
def create_kafka_config() -> Dict[str, Any]:
    """Crea configurazione Kafka con SSL."""
    return {
        "bootstrap.servers": KAFKA_BROKER,
        "group.id": CONSUMER_GROUP,
        "security.protocol": "SSL",
        "ssl.ca.location": SSL_CAFILE,
        "ssl.certificate.location": SSL_CERTFILE,
        "ssl.key.location": SSL_KEYFILE,
        "auto.offset.reset": "latest",
        "enable.auto.commit": "false",
    }

# Parser per messaggi Kafka
def parse_kafka_message(msg: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Parsa messaggio Kafka e restituisce (key, value)."""
    try:
        # Decodifica JSON se necessario
        if isinstance(msg.get("value"), bytes):
            value = json.loads(msg["value"].decode("utf-8"))
        else:
            value = msg.get("value", {})
        
        # Usa user_id come chiave per partitioning
        key = str(value.get("user_id", "unknown"))
        
        # Aggiungi offset per tracking
        value["_offset"] = msg.get("offset", 0)
        
        return (key, value)
    except Exception as e:
        logger.error(f"Errore parsing messaggio: {e}")
        return ("error", {"error": str(e)})

# Costruzione del dataflow
def build_dataflow() -> Dataflow:
    """Costruisce il dataflow Bytewax."""
    flow = Dataflow("nearyou_consumer")
    
    # Inizializza connessioni database (singleton pattern)
    db_conn = DatabaseConnections()
    
    # 1. Input: leggi da Kafka
    kafka_config = create_kafka_config()
    stream = op.input("kafka_input", flow, 
                      KafkaSource([KAFKA_TOPIC], brokers=kafka_config))
    
    # 2. Parse messaggi
    parsed = op.map("parse", stream, parse_kafka_message)
    
    # 3. Filtra messaggi errati
    valid_messages = op.filter("filter_valid", parsed, 
                               lambda x: x[0] != "error" and "user_id" in x[1])
    
    # 4. Arricchisci con negozio più vicino (async operation)
    enriched = op.flat_map("enrich_shop", valid_messages, 
                           lambda x: enrich_with_nearest_shop(x, db_conn))
    
    # 5. Genera messaggio se in prossimità (con cache)
    with_messages = op.flat_map("generate_msg", enriched,
                                lambda x: check_proximity_and_generate_message(x, db_conn))
    
    # 6. Scrivi su ClickHouse (side effect)
    op.inspect("write_clickhouse", with_messages, 
               lambda x: write_to_clickhouse(x, db_conn))
    
    # 7. Log finale per debugging
    op.inspect("log_processed", with_messages, 
               lambda x: logger.info(f"Processato evento per user {x[0]}: "
                                    f"shop={x[1].get('shop_name')} "
                                    f"distance={x[1].get('distance'):.1f}m"))
    
    return flow

# Entry point per Bytewax CLI
if __name__ == "__main__":
    # Costruisci il dataflow
    flow = build_dataflow()
    
    # Avvia con CLI (supporta multi-worker, recovery, etc.)
    cli_main(flow)