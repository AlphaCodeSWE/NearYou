"""
Test unitari per le API della dashboard.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Importa il modulo da testare
from services.dashboard.main_user import app
from services.dashboard.auth import authenticate_user, create_access_token


@pytest.mark.unit
class TestDashboardAPI:
    
    def setup_method(self):
        """Setup per i test."""
        self.client = TestClient(app)
    
    @patch("services.dashboard.auth.ch")
    def test_login_success(self, mock_ch):
        """Testa il login con credenziali valide."""
        # Setup del mock
        mock_ch.execute.return_value = [(1, "password123")]
        
        # Esecuzione
        response = self.client.post(
            "/api/token",
            data={"username": "testuser", "password": "password123"},
        )
        
        # Verifica
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    
    @patch("services.dashboard.auth.ch")
    def test_login_invalid_credentials(self, mock_ch):
        """Testa il login con credenziali non valide."""
        # Setup del mock
        mock_ch.execute.return_value = [(1, "password123")]
        
        # Esecuzione
        response = self.client.post(
            "/api/token",
            data={"username": "testuser", "password": "wrong_password"},
        )
        
        # Verifica
        assert response.status_code == 400
        assert "detail" in response.json()
    
    def test_user_dashboard(self):
        """Testa l'endpoint della dashboard utente."""
        # Esecuzione
        response = self.client.get("/dashboard/user")
        
        # Verifica
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    @patch("services.dashboard.api.routes.get_current_user")
    @patch("services.dashboard.api.routes.get_clickhouse_client")
    def test_get_user_profile(self, mock_ch_client, mock_get_current_user):
        """Testa l'endpoint del profilo utente."""
        # Setup dei mock
        mock_get_current_user.return_value = {"user_id": 1}
        
        ch_instance = MagicMock()
        ch_instance.execute.return_value = [(1, 30, "Ingegnere", "tecnologia, viaggi")]
        mock_ch_client.return_value.__enter__.return_value = ch_instance
        
        # Esecuzione
        response = self.client.get(
            "/api/user/profile",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Verifica
        assert response.status_code == 200
        assert response.json()["user_id"] == 1
        assert response.json()["age"] == 30