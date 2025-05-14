"""
Test unitari per il consumer Kafka.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

# Importa il modulo da testare
from src.data_pipeline.consumer import get_user_profile, get_shop_category, get_personalized_message

@pytest.mark.unit
class TestConsumerFunctions:
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, mock_clickhouse_client):
        """Testa la funzione get_user_profile."""
        # Setup del mock
        user_id = 1
        mock_clickhouse_client.execute.return_value = [
            (1, 30, "Ingegnere", "tecnologia, viaggi")
        ]
        
        # Esecuzione
        result = await get_user_profile(mock_clickhouse_client, user_id)
        
        # Verifica
        assert result is not None
        assert result["user_id"] == 1
        assert result["age"] == 30
        assert result["profession"] == "Ingegnere"
        assert result["interests"] == "tecnologia, viaggi"
        
        # Verifica chiamata al client
        mock_clickhouse_client.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_shop_category(self):
        """Testa la funzione get_shop_category."""
        # Setup del mock
        mock_pool = AsyncMock()
        mock_pool.fetchrow.return_value = {"category": "ristorante"}
        
        # Esecuzione
        result = await get_shop_category(mock_pool, 1)
        
        # Verifica
        assert result == "ristorante"
        mock_pool.fetchrow.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_personalized_message(self):
        """Testa la funzione get_personalized_message."""
        # Setup dei dati
        user_data = {
            "user_id": 1,
            "age": 30,
            "profession": "Ingegnere",
            "interests": "tecnologia, viaggi"
        }
        
        poi_data = {
            "name": "Caffè Milano",
            "category": "bar",
            "description": "Negozio a 50m di distanza"
        }
        
        # Mock di httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client:
            # Configura il comportamento del mock
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": "Ciao Ingegnere! Ti meriti una pausa al Caffè Milano!",
                "cached": False
            }
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Esecuzione
            result = await get_personalized_message(user_data, poi_data)
            
            # Verifica
            assert result == "Ciao Ingegnere! Ti meriti una pausa al Caffè Milano!"
            
            # Verifica chiamata API
            mock_client_instance.post.assert_called_once()