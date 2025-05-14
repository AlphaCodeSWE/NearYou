"""
Test unitari per il servizio di generazione messaggi.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.message_generator.services.generator_service import MessageGeneratorService
from services.message_generator.models.message import UserProfile, PointOfInterest


@pytest.mark.unit
class TestMessageGeneratorService:
    
    def test_init(self):
        """Testa l'inizializzazione del service."""
        # Setup
        llm_client = MagicMock()
        prompt_template = "Test prompt {age}"
        
        # Esecuzione
        service = MessageGeneratorService(llm_client, prompt_template)
        
        # Verifica
        assert service.llm_client == llm_client
        assert "Test prompt" in service.prompt_template.template
    
    @patch("services.message_generator.services.generator_service.cache_utils")
    def test_generate_message_cache_hit(self, mock_cache_utils):
        """Testa la generazione di messaggi con cache hit."""
        # Setup
        llm_client = MagicMock()
        prompt_template = "Test prompt"
        service = MessageGeneratorService(llm_client, prompt_template)
        
        user_params = {"age": 30, "profession": "Ingegnere", "interests": "tech"}
        poi_params = {"name": "CafeTest", "category": "bar", "description": ""}
        
        # Configura il mock per simulare un cache hit
        mock_cache_utils.get_cached_message.return_value = "Messaggio dalla cache"
        
        # Esecuzione
        message, is_cached = service.generate_message(user_params, poi_params)
        
        # Verifica
        assert message == "Messaggio dalla cache"
        assert is_cached is True
        mock_cache_utils.get_cached_message.assert_called_once_with(user_params, poi_params)
        # Verifica che _call_llm non sia stato chiamato
        llm_client.assert_not_called()
    
    @patch("services.message_generator.services.generator_service.cache_utils")
    def test_generate_message_cache_miss(self, mock_cache_utils):
        """Testa la generazione di messaggi con cache miss."""
        # Setup
        llm_client = MagicMock()
        llm_client.return_value.content = "Messaggio generato dal LLM"
        prompt_template = "Test prompt {age}"
        service = MessageGeneratorService(llm_client, prompt_template)
        
        user_params = {"age": 30, "profession": "Ingegnere", "interests": "tech"}
        poi_params = {"name": "CafeTest", "category": "bar", "description": ""}
        
        # Configura il mock per simulare un cache miss
        mock_cache_utils.get_cached_message.return_value = None
        
        # Patch del metodo _call_llm
        with patch.object(service, '_call_llm', return_value="Messaggio generato dal LLM") as mock_call_llm:
            # Esecuzione
            message, is_cached = service.generate_message(user_params, poi_params)
            
            # Verifica
            assert message == "Messaggio generato dal LLM"
            assert is_cached is False
            mock_cache_utils.get_cached_message.assert_called_once_with(user_params, poi_params)
            mock_call_llm.assert_called_once_with(user_params, poi_params)
            mock_cache_utils.cache_message.assert_called_once_with(user_params, poi_params, "Messaggio generato dal LLM")