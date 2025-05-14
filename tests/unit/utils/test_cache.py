"""
Test unitari per il sistema di cache.
"""
import pytest
import time
from unittest.mock import patch, MagicMock

from src.cache.memory_cache import MemoryCache
from src.cache.redis_cache import RedisCache

@pytest.mark.unit
class TestMemoryCache:
    
    def test_init(self):
        """Testa l'inizializzazione della cache."""
        # Esecuzione
        cache = MemoryCache(default_ttl=120)
        
        # Verifica
        assert cache.default_ttl == 120
        assert cache.cache == {}
        
    def test_set_and_get(self):
        """Testa le operazioni set e get."""
        # Setup
        cache = MemoryCache()
        
        # Esecuzione
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        
        # Verifica
        assert result == "test_value"
        
    def test_expiration(self):
        """Testa la scadenza delle chiavi."""
        # Setup
        cache = MemoryCache()
        
        # Esecuzione
        cache.set("test_key", "test_value", ttl=1)  # 1 secondo TTL
        
        # Verifica prima della scadenza
        assert cache.get("test_key") == "test_value"
        
        # Attendi la scadenza
        time.sleep(1.1)
        
        # Verifica dopo la scadenza
        assert cache.get("test_key") is None
        
    def test_delete(self):
        """Testa l'eliminazione delle chiavi."""
        # Setup
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        
        # Esecuzione
        result = cache.delete("test_key")
        
        # Verifica
        assert result is True
        assert cache.get("test_key") is None
        
    def test_exists(self):
        """Testa il controllo di esistenza."""
        # Setup
        cache = MemoryCache()
        cache.set("test_key", "test_value")
        
        # Esecuzione e verifica
        assert cache.exists("test_key") is True
        assert cache.exists("non_existent_key") is False
        
    def test_info(self):
        """Testa il recupero delle statistiche."""
        # Setup
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Esecuzione
        info = cache.info()
        
        # Verifica
        assert info["status"] == "in-memory"
        assert info["total_keys"] == 2
        assert info["active_keys"] >= 2


@pytest.mark.unit
class TestRedisCache:
    
    @patch("src.cache.redis_cache.redis.Redis")
    def test_init(self, mock_redis):
        """Testa l'inizializzazione della cache Redis."""
        # Setup
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance
        
        # Esecuzione
        cache = RedisCache(host="localhost", port=6379, db=0)
        
        # Verifica
        assert cache.default_ttl == 86400
        assert cache.client == mock_redis_instance
        mock_redis.assert_called_once()
        
    @patch("src.cache.redis_cache.redis.Redis")
    def test_set_and_get(self, mock_redis):
        """Testa le operazioni set e get con Redis."""
        # Setup
        mock_redis_instance = MagicMock()
        # Configura mock per get
        mock_redis_instance.get.return_value = b'"test_value"'
        mock_redis.return_value = mock_redis_instance
        
        cache = RedisCache()
        
        # Esecuzione
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        
        # Verifica
        assert result == "test_value"
        mock_redis_instance.setex.assert_called_once_with("test_key", 86400, b'"test_value"')
        mock_redis_instance.get.assert_called_once_with("test_key")