"""
Configurazione globale per i test pytest.
Contiene fixture condivise tra i diversi livelli di test.
"""
import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch

# Imposta l'ambiente di test
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["CACHE_ENABLED"] = "false"

# Fixture per client ClickHouse mock
@pytest.fixture
def mock_clickhouse_client():
    """Restituisce un mock del client ClickHouse per i test."""
    client = MagicMock()
    # Configura comportamenti default se necessario
    client.execute.return_value = []
    return client

# Fixture per client Kafka mock
@pytest.fixture
def mock_kafka_producer():
    """Restituisce un mock del producer Kafka per i test."""
    producer = MagicMock()
    # Configura comportamenti default
    return producer

# Fixture per API client
@pytest.fixture
async def test_client():
    """Crea un client di test per le API FastAPI."""
    from fastapi.testclient import TestClient
    from services.dashboard.main_user import app
    
    client = TestClient(app)
    return client

# Fixture per loop asyncio
@pytest.fixture
def event_loop():
    """Crea un nuovo event loop per i test asyncio."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()