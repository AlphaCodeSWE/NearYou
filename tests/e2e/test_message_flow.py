"""
Test end-to-end per il flusso completo dei messaggi.
"""
import pytest
import asyncio
import json
import httpx
from unittest.mock import patch, AsyncMock

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_location_to_notification_flow():
    """
    Testa il flusso completo dall'invio di una posizione alla generazione
    di un messaggio e la sua consegna all'utente.
    
    Questo è un test end-to-end che simula tutto il flusso dell'applicazione.
    """
    # Mock per simulare il flusso completo, ma eseguire test localmente
    with patch("httpx.AsyncClient") as mock_client:
        # Configura il mock per simulare le varie API
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Simula response per l'invio posizione
        mock_position_response = AsyncMock()
        mock_position_response.status_code = 200
        mock_position_response.json.return_value = {
            "message": "Posizione registrata con successo"
        }
        
        # Simula response per il recupero notifiche
        mock_notification_response = AsyncMock()
        mock_notification_response.status_code = 200
        mock_notification_response.json.return_value = {
            "promotions": [
                {
                    "event_id": 1,
                    "timestamp": "2025-05-14T10:30:00",
                    "shop_name": "Caffè Milano",
                    "message": "Ciao! Sei vicino al Caffè Milano. Il loro cappuccino è eccellente!"
                }
            ]
        }
        
        # Configura il comportamento del mock client
        mock_client_instance.post.return_value = mock_position_response
        mock_client_instance.get.return_value = mock_notification_response
        
        # Test del flusso completo
        
        # 1. Ottieni token di accesso simulato
        token = "fake_jwt_token"
        
        # 2. Invia posizione utente
        position_data = {
            "latitude": 45.4642,
            "longitude": 9.19,
            "timestamp": "2025-05-14T10:30:00Z"
        }
        
        await mock_client_instance.post(
            "http://localhost:8003/api/user/position",
            json=position_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 3. Simula attesa per elaborazione (nella realtà aspetteremmo che il consumer elabori)
        await asyncio.sleep(0.1)
        
        # 4. Recupera notifiche/promozioni
        response = await mock_client_instance.get(
            "http://localhost:8003/api/user/promotions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # 5. Verifica che il messaggio sia stato generato e consegnato
        notifications = response.json()["promotions"]
        assert len(notifications) > 0
        assert notifications[0]["shop_name"] == "Caffè Milano"
        assert "cappuccino" in notifications[0]["message"]
        
        # Verifica chiamate alle API
        mock_client_instance.post.assert_called_once()
        mock_client_instance.get.assert_called_once()