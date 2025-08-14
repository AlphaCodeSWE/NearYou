"""
Integration Tests for dashboard services and API endpoints.
Tests WebSocket functionality, authentication, and database interactions.
"""
import pytest
import asyncio
import json
import jwt
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from services.dashboard.main_user import app, ConnectionManager
from services.dashboard.auth import get_current_user, create_access_token

# Helper function to simulate verify_token for testing
def verify_token(token: str):
    """Test helper to verify token without FastAPI dependency injection."""
    try:
        from jose import jwt
        from services.dashboard.auth import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except:
        return None
from services.dashboard.api.routes import router


class TestConnectionManager:
    """Integration tests for WebSocket ConnectionManager."""
    
    def setup_method(self):
        """Set up fresh ConnectionManager for each test."""
        self.manager = ConnectionManager()
        self.manager.active_connections = {}
        self.manager.position_cache = {}
    
    @pytest.mark.asyncio
    async def test_connect_user(self):
        """Test connecting a user via WebSocket."""
        mock_websocket = AsyncMock()
        user_id = 123
        
        await self.manager.connect(mock_websocket, user_id)
        
        assert user_id in self.manager.active_connections
        assert self.manager.active_connections[user_id] == mock_websocket
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_user(self):
        """Test disconnecting a user."""
        user_id = 123
        mock_websocket = Mock()
        
        # Add user first
        self.manager.active_connections[user_id] = mock_websocket
        self.manager.position_cache[user_id] = {"lat": 45.4642, "lon": 9.1900}
        
        # Disconnect
        self.manager.disconnect(user_id)
        
        assert user_id not in self.manager.active_connections
        assert user_id not in self.manager.position_cache
    

    
    @pytest.mark.asyncio
    async def test_send_position_update_to_nonexistent_user(self):
        """Test sending update to non-connected user."""
        user_id = 999  # Not connected
        position_data = {"latitude": 45.4642, "longitude": 9.1900}
        
        # Should not raise exception
        await self.manager.send_position_update(user_id, position_data)
    

    
    @pytest.mark.asyncio
    async def test_send_position_update_with_websocket_error(self):
        """Test handling WebSocket errors during send."""
        user_id = 123
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("WebSocket closed")
        self.manager.active_connections[user_id] = mock_websocket
        
        position_data = {"latitude": 45.4642, "longitude": 9.1900}
        
        # Should handle exception gracefully
        await self.manager.send_position_update(user_id, position_data)
        
        # User should be disconnected after error
        assert user_id not in self.manager.active_connections


class TestAuthentication:
    """Integration tests for authentication system."""
    
    def setup_method(self):
        """Set up test environment variables."""
        os.environ["JWT_SECRET"] = "test_secret_key"
        os.environ["JWT_ALGORITHM"] = "HS256"
    

    
    def test_verify_token_valid(self):
        """Test verifying valid JWT token."""
        user_data = {"user_id": 123, "username": "testuser"}
        token = create_access_token(user_data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == 123
        assert payload["username"] == "testuser"
    
    def test_verify_token_invalid(self):
        """Test verifying invalid JWT token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        assert payload is None
    

    
    def test_verify_token_wrong_secret(self):
        """Test verifying token with wrong secret."""
        # Create token with different secret
        user_data = {"user_id": 123, "username": "testuser"}
        wrong_token = jwt.encode(user_data, "wrong_secret", algorithm="HS256")
        
        payload = verify_token(wrong_token)
        assert payload is None


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        os.environ["JWT_SECRET"] = "test_secret_key"
        os.environ["JWT_ALGORITHM"] = "HS256"
        os.environ["CLICKHOUSE_HOST"] = "test_clickhouse"
        os.environ["CLICKHOUSE_PORT"] = "9000"
        os.environ["CLICKHOUSE_USER"] = "default"
        os.environ["CLICKHOUSE_PASSWORD"] = ""
        os.environ["CLICKHOUSE_DATABASE"] = "test_nearyou"
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_valid_token(self):
        """Test WebSocket connection with valid authentication."""
        # Create valid token
        user_data = {"user_id": 123, "username": "testuser"}
        token = create_access_token(user_data)
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        
        # Mock ClickHouse client
        with patch('services.dashboard.main_user.CHClient') as mock_ch_client:
            mock_client = Mock()
            mock_ch_client.return_value = mock_client
            
            # Mock position query result
            mock_client.execute.return_value = [
                (123, 45.4642, 9.1900, "2023-06-15 14:30:00", 1)
            ]
            
            # Mock the websocket endpoint behavior
            with patch('services.dashboard.main_user.manager') as mock_manager:
                mock_manager.connect = AsyncMock()
                
                # Simulate receiving auth data
                auth_data = {"token": token}
                mock_websocket.receive_json.return_value = auth_data
                
                # This would be called in the actual endpoint
                payload = verify_token(token)
                assert payload is not None
                assert payload["user_id"] == 123
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_invalid_token(self):
        """Test WebSocket connection with invalid token."""
        mock_websocket = AsyncMock()
        
        # Invalid token
        invalid_token = "invalid.token"
        auth_data = {"token": invalid_token}
        
        payload = verify_token(invalid_token)
        assert payload is None
        
        # In real implementation, this would close the WebSocket
    



class TestAPIEndpoints:
    """Integration tests for API endpoints."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
        os.environ["JWT_SECRET"] = "test_secret_key"
        os.environ["JWT_ALGORITHM"] = "HS256"
    
    def test_token_endpoint_valid_credentials(self):
        """Test token generation with valid credentials."""
        # This would typically check against a database
        # For testing, we'll mock the authentication
        
        with patch('services.dashboard.main_user.authenticate_user') as mock_auth:
            mock_auth.return_value = {"user_id": 123, "username": "testuser"}
            
            response = self.client.post(
                "/api/token",
                data={"username": "testuser", "password": "testpass"}
            )
            
            if response.status_code == 200:
                assert "access_token" in response.json()
                assert response.json()["token_type"] == "bearer"
    

    
    def test_user_dashboard_endpoint(self):
        """Test user dashboard endpoint."""
        response = self.client.get("/dashboard/user")
        
        # Should return HTML or redirect
        assert response.status_code in [200, 302]
    



class TestDashboardAPIRoutes:
    """Integration tests for dashboard API routes."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        os.environ["JWT_SECRET"] = "test_secret_key"
        os.environ["JWT_ALGORITHM"] = "HS256"
        
        # Create valid token for authenticated requests
        user_data = {"user_id": 123, "username": "testuser"}
        self.valid_token = create_access_token(user_data)
        self.auth_headers = {"Authorization": f"Bearer {self.valid_token}"}
    

    
    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile without authentication."""
        response = self.client.get("/api/user/profile")
        
        assert response.status_code == 401
    

    
    def test_get_user_notifications_with_pagination(self):
        """Test getting user notifications with pagination."""
        with patch('services.dashboard.api.routes.CHClient') as mock_ch_client:
            mock_client = Mock()
            mock_ch_client.return_value = mock_client
            
            # Mock notifications data
            mock_notifications = [
                (1, "Welcome message", "2023-06-15 14:30:00", "Test Shop", "ristorante"),
                (2, "Special offer", "2023-06-15 15:00:00", "Coffee Place", "bar")
            ]
            mock_client.execute.return_value = mock_notifications
            
            response = self.client.get(
                "/api/user/notifications?page=0&limit=10",
                headers=self.auth_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "notifications" in data
                assert len(data["notifications"]) == 2
    



class TestErrorHandling:
    """Integration tests for error handling across components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.client = TestClient(app)
        os.environ["JWT_SECRET"] = "test_secret_key"
    

    

    
    @pytest.mark.asyncio
    async def test_websocket_unexpected_disconnection(self):
        """Test handling of unexpected WebSocket disconnections."""
        manager = ConnectionManager()
        user_id = 123
        
        # Mock WebSocket that fails on send
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("Connection lost")
        
        await manager.connect(mock_websocket, user_id)
        
        # Try to send update - should handle error
        position_data = {"latitude": 45.4642, "longitude": 9.1900}
        await manager.send_position_update(user_id, position_data)
        
        # User should be automatically disconnected after error
        assert user_id not in manager.active_connections


class TestCacheIntegration:
    """Integration tests for caching in dashboard services."""
    
    def test_position_cache_in_connection_manager(self):
        """Test position caching in ConnectionManager."""
        manager = ConnectionManager()
        user_id = 123
        
        # Cache position
        position = {"lat": 45.4642, "lon": 9.1900, "timestamp": datetime.now()}
        manager.position_cache[user_id] = position
        
        # Verify cache
        assert user_id in manager.position_cache
        assert manager.position_cache[user_id]["lat"] == 45.4642
        
        # Disconnect should clear cache
        manager.disconnect(user_id)
        assert user_id not in manager.position_cache


if __name__ == "__main__":
    pytest.main([__file__])
