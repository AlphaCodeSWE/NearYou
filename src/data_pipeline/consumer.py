#!/usr/bin/env python3
import os
import asyncio
import ssl
import json
import logging                
from datetime import datetime, timezone

import asyncpg
import httpx
from aiokafka import AIOKafkaConsumer
from clickhouse_driver import Client as CHClient

from src.utils.logger_config import setup_logging
from src.configg import (
    KAFKA_BROKER, KAFKA_TOPIC, CONSUMER_GROUP,
    SSL_CAFILE, SSL_CERTFILE, SSL_KEYFILE,
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE,
    MESSAGE_GENERATOR_URL,
)
from src.utils.utils import wait_for_broker

logger = logging.getLogger(__name__)
setup_logging()

# Configurazione soglia distanza per messaggi (in metri)
MAX_POI_DISTANCE = 200  # Utenti entro 200m riceveranno messaggi

async def wait_for_postgres(retries: int = 30, delay: int = 2):
    for i in range(retries):
        try:
            conn = await asyncpg.connect(
                host=POSTGRES_HOST, port=POSTGRES_PORT,
                user=POSTGRES_USER, password=POSTGRES_PASSWORD,
                database=POSTGRES_DB
            )
            await conn.close()
            logger.info("Postgres è pronto")
            return
        except Exception:
            logger.debug("Postgres non pronto (tentativo %d/%d)", i+1, retries)
            await asyncio.sleep(delay)
    raise RuntimeError("Postgres non pronto dopo troppe prove")

async def wait_for_clickhouse(retries: int = 30, delay: int = 2):
    for i in range(retries):
        try:
            ch = CHClient(
                host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
                user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD,
                database=CLICKHOUSE_DATABASE
            )
            ch.execute("SELECT 1")
            logger.info("ClickHouse è pronto")
            return
        except Exception:
            logger.debug("ClickHouse non pronto (tentativo %d/%d)", i+1, retries)
            await asyncio.sleep(delay)
    raise RuntimeError("ClickHouse non pronto dopo troppe prove")

async def get_user_profile(ch_client, user_id):
    """Recupera il profilo dell'utente da ClickHouse."""
    try:
        result = ch_client.execute(
            """
            SELECT
                user_id, age, profession, interests
            FROM users
            WHERE user_id = %(user_id)s
            LIMIT 1
            """,
            {"user_id": user_id}
        )
        if not result:
            logger.warning(f"Profilo utente {user_id} non trovato")
            return None
            
        user_data = {
            "user_id": result[0][0],
            "age": result[0][1],
            "profession": result[0][2],
            "interests": result[0][3]
        }
        return user_data
    except Exception as e:
        logger.error(f"Errore recupero profilo utente {user_id}: {e}")
        return None

async def get_shop_category(pool, shop_id):
    """Recupera la categoria del negozio da PostgreSQL."""
    try:
        row = await pool.fetchrow(
            "SELECT category FROM shops WHERE shop_id = $1",
            shop_id
        )
        return row["category"] if row else "negozio"
    except Exception as e:
        logger.error(f"Errore recupero categoria negozio {shop_id}: {e}")
        return "negozio"

async def get_personalized_message(user_data, poi_data):
    """Ottieni messaggio personalizzato dal message generator."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Prepara il payload con solo i campi necessari
            payload = {
                "user": {
                    "age": user_data["age"],
                    "profession": user_data["profession"],
                    "interests": user_data["interests"]
                },
                "poi": poi_data
            }
            
            logger.debug(f"Chiamata message-generator con payload: {payload}")
            response = await client.post(MESSAGE_GENERATOR_URL, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Errore message-generator: {response.status_code} - {response.text}")
                return ""
                
            result = response.json()
            logger.info(f"Messaggio generato per utente {user_data['user_id']} in {poi_data['name']}: {result['message'][:30]}...")
            return result["message"]
    except Exception as e:
        logger.error(f"Errore chiamata message-generator: {e}")
        return ""

async def consumer_loop():
    # 1) Readiness
    host, port = KAFKA_BROKER.split(":")
    await asyncio.gather(
        asyncio.get_event_loop().run_in_executor(None, wait_for_broker, host, int(port)),
        wait_for_postgres(),
        wait_for_clickhouse(),
    )
    logger.info("Kafka, Postgres e ClickHouse sono pronti")

    # 2) SSL context per Kafka
    ssl_ctx = ssl.create_default_context(cafile=SSL_CAFILE)
    ssl_ctx.load_cert_chain(certfile=SSL_CERTFILE, keyfile=SSL_KEYFILE)

    # 3) Inizializza consumer
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        security_protocol="SSL",
        ssl_context=ssl_ctx,
        group_id=CONSUMER_GROUP,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    await consumer.start()

    # 4) Pool PostgreSQL e client ClickHouse
    pg_pool = await asyncpg.create_pool(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        min_size=1, max_size=5
    )
    ch = CHClient(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
        user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE
    )

    try:
        async for msg in consumer:
            data = msg.value
            try:
                # Estrai user_id
                user_id = data["user_id"]
                
                # Parse timestamp ISO -> datetime (rimuovo tzinfo per ClickHouse)
                ts = datetime.fromisoformat(data["timestamp"]).astimezone(timezone.utc).replace(tzinfo=None)

                # Cerca il negozio più vicino
                row = await pg_pool.fetchrow(
                    """
                    SELECT
                      shop_id,
                      shop_name,
                      category,
                      ST_Distance(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
                      ) AS distance
                    FROM shops
                    ORDER BY distance
                    LIMIT 1
                    """,
                    data["longitude"], data["latitude"]
                )
                
                shop_id = row["shop_id"]
                shop_name = row["shop_name"]
                shop_category = row["category"]
                distance = row["distance"]
                
                # Inizializza poi_info vuoto
                poi_info = ""
                
                # Se l'utente è abbastanza vicino, genera un messaggio personalizzato
                if distance <= MAX_POI_DISTANCE:
                    logger.info(f"Utente {user_id} vicino a {shop_name} (d={distance:.1f}m). Generazione messaggio...")
                    
                    # Ottieni il profilo utente
                    user_profile = await get_user_profile(ch, user_id)
                    
                    if user_profile:
                        # Dati POI per il messaggio
                        poi_data = {
                            "name": shop_name,
                            "category": shop_category,
                            "description": f"Negozio a {distance:.0f}m di distanza"
                        }
                        
                        # Chiamata al message generator
                        poi_info = await get_personalized_message(user_profile, poi_data)
                    else:
                        logger.warning(f"Impossibile generare messaggio: profilo utente {user_id} non trovato")
                else:
                    logger.debug(f"Utente {user_id} troppo lontano da {shop_name} (d={distance:.1f}m > {MAX_POI_DISTANCE}m)")

                # Scrivi in ClickHouse con eventuale messaggio
                ch.execute(
                    """
                    INSERT INTO user_events
                      (event_id, event_time, user_id, latitude, longitude, poi_range, poi_name, poi_info)
                    VALUES
                    """,
                    [
                        (msg.offset,
                         ts,
                         user_id,
                         data["latitude"],
                         data["longitude"],
                         distance,
                         shop_name,
                         poi_info)
                    ]
                )
                
                if poi_info:
                    logger.info(f"Evento con messaggio per utente {user_id} → negozio '{shop_name}' (d={distance:.1f}m)")
                else:
                    logger.debug(f"Evento senza messaggio per utente {user_id} → negozio '{shop_name}' (d={distance:.1f}m)")
                
            except Exception as e:
                logger.error(f"Errore elaborazione messaggio {msg}: {e}")
    finally:
        await consumer.stop()
        await pg_pool.close()

if __name__ == "__main__":
    asyncio.run(consumer_loop())