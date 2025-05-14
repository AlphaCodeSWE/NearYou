"""
Test di integrazione per il flusso Kafka producer-consumer.
"""
import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

from src.data_pipeline.producer import producer_worker
from src.data_pipeline.consumer import consumer_loop


@pytest.mark.integration
@pytest.mark.asyncio
async def test_producer_to_consumer_flow():
    """
    Testa il flusso dal producer al consumer attraverso Kafka.
    
    Questo test simula il flusso di dati da un producer a un consumer
    attraverso un mock di Kafka, verificando che i messaggi vengano 
    correttamente elaborati.
    """
    # Setup dei mock
    mock_producer = AsyncMock()
    mock_producer.send_and_wait = AsyncMock()
    
    # Simula un utente
    user = (1, 30, "Ingegnere", "tecnologia, viaggi")
    
    # Crea un evento per sincronizzare producer e consumer
    message_sent_event = asyncio.Event()
    
    # Mock per la funzione fetch_route
    async def mock_fetch_route(*args, **kwargs):
        return [
            {"lon": 9.18, "lat": 45.46},
            {"lon": 9.19, "lat": 45.47}
        ]
    
    # Patch della funzione fetch_route
    with patch("src.data_pipeline.producer.fetch_route", mock_fetch_route):
        # Monkey patch di send_and_wait per tracciare il messaggio inviato
        original_send_and_wait = mock_producer.send_and_wait
        sent_message = None
        
        async def traced_send_and_wait(topic, value):
            nonlocal sent_message
            sent_message = value
            message_sent_event.set()  # Segnala che il messaggio è stato inviato
            return await original_send_and_wait(topic, value)
        
        mock_producer.send_and_wait = traced_send_and_wait
        
        # Avvia il producer in background
        producer_task = asyncio.create_task(
            producer_worker(mock_producer, user)
        )
        
        # Attendi che il producer invii un messaggio
        await asyncio.wait_for(message_sent_event.wait(), timeout=5.0)
        
        # Ora possiamo cancellare il producer task
        producer_task.cancel()
        
        # Verifica il messaggio inviato
        assert sent_message is not None
        assert sent_message["user_id"] == 1
        assert sent_message["age"] == 30
        assert sent_message["profession"] == "Ingegnere"
        assert "latitude" in sent_message
        assert "longitude" in sent_message
        
        # Ora testiamo il consumer con questo messaggio
        # Setup dei mock per il consumer
        with patch("aiokafka.AIOKafkaConsumer") as mock_consumer_class:
            mock_consumer = AsyncMock()
            mock_consumer_class.return_value = mock_consumer
            
            # Simula il messaggio Kafka
            mock_message = MagicMock()
            mock_message.value = json.dumps(sent_message)
            mock_message.offset = 1
            
            # Configura il consumer per restituire il messaggio e poi fermarsi
            mock_consumer.__aiter__.return_value = [mock_message]
            
            # Mock per postgres e clickhouse
            with patch("asyncpg.create_pool") as mock_pg_pool, \
                 patch("src.data_pipeline.consumer.CHClient") as mock_ch:
                
                # Configura postgres mock
                pg_pool = AsyncMock()
                pg_pool.fetchrow.return_value = {
                    "shop_id": 1,
                    "shop_name": "Caffè Milano",
                    "category": "bar",
                    "distance": 50.0
                }
                mock_pg_pool.return_value = pg_pool
                
                # Configura clickhouse mock
                ch_client = MagicMock()
                ch_client.execute.return_value = None
                mock_ch.return_value = ch_client
                
                # Mock per get_personalized_message
                with patch("src.data_pipeline.consumer.get_personalized_message", 
                          return_value=AsyncMock(return_value="Messaggio personalizzato")):
                    
                    # Patch delle funzioni di wait
                    with patch("src.data_pipeline.consumer.wait_for_postgres", return_value=None), \
                         patch("src.data_pipeline.consumer.wait_for_clickhouse", return_value=None), \
                         patch("src.data_pipeline.consumer.wait_for_broker", return_value=None):
                        
                        # Esegui il consumer per un breve periodo e poi fermati
                        consumer_task = asyncio.create_task(consumer_loop())
                        await asyncio.sleep(0.1)  # Consenti al consumer di elaborare il messaggio
                        consumer_task.cancel()
                        
                        # Verifica che clickhouse sia stato chiamato per salvare l'evento
                        ch_client.execute.assert_called()
                        
                        # Verifica che postgres sia stato interrogato per trovare il negozio più vicino
                        pg_pool.fetchrow.assert_called()