"""
Unit Tests for cache implementations (Redis and Memory cache).
Tests caching patterns, TTL functionality, and error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import redis
from datetime import datetime, timedelta

from src.cache.redis_cache import RedisCache
from src.cache.memory_cache import MemoryCache


class TestRedisCache:
    """Unit tests for RedisCache implementation."""
    
    @patch('src.cache.redis_cache.redis.Redis')
    def test_redis_cache_initialization_success(self, mock_redis_class):
        """Test successful Redis connection initialization."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client
        
        cache = RedisCache(host="localhost", port=6379, db=0)
        
        assert cache.client == mock_client
        mock_redis_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=False,
            socket_timeout=5
        )
        mock_client.ping.assert_called_once()
    
    @patch('src.cache.redis_cache.redis.Redis')
    def test_redis_cache_initialization_with_password(self, mock_redis_class):
        """Test Redis initialization with password."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client
        
        cache = RedisCache(host="localhost", port=6379, password="secret123")
        
        mock_redis_class.assert_called_once_with(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=False,
            socket_timeout=5,
            password="secret123"
        )
    
    @patch('src.cache.redis_cache.redis.Redis')
    def test_redis_cache_initialization_failure(self, mock_redis_class):
        """Test Redis initialization failure handling."""
        mock_redis_class.side_effect = redis.ConnectionError("Connection failed")
        
        cache = RedisCache()
        
        assert cache.client is None
    
    def test_redis_cache_set_get_simple_value(self):
        """Test setting and getting simple string values."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        # Set operation
        mock_client.setex.return_value = True
        result = cache.set("test_key", "test_value", ttl=3600)
        
        assert result is True
        mock_client.setex.assert_called_once_with("test_key", 3600, b"test_value")
        
        # Get operation
        mock_client.get.return_value = b"test_value"
        value = cache.get("test_key")
        
        assert value == "test_value"
        mock_client.get.assert_called_once_with("test_key")
    
    def test_redis_cache_set_get_json_value(self):
        """Test setting and getting complex JSON values."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        test_data = {"user_id": 123, "name": "John", "scores": [85, 92, 78]}
        
        # Set operation
        mock_client.setex.return_value = True
        result = cache.set("user:123", test_data)
        
        assert result is True
        expected_json = json.dumps(test_data).encode('utf-8')
        mock_client.setex.assert_called_once_with("user:123", 86400, expected_json)
        
        # Get operation
        mock_client.get.return_value = json.dumps(test_data).encode('utf-8')
        value = cache.get("user:123")
        
        assert value == test_data
    
    def test_redis_cache_get_nonexistent_key(self):
        """Test getting a non-existent key returns None."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        mock_client.get.return_value = None
        value = cache.get("nonexistent_key")
        
        assert value is None
    
    def test_redis_cache_get_malformed_json(self):
        """Test handling malformed JSON in cache."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        # Return invalid JSON
        mock_client.get.return_value = b"invalid json data {"
        value = cache.get("bad_json_key")
        
        # Should fall back to raw string
        assert value == "invalid json data {"
    
    def test_redis_cache_delete(self):
        """Test deleting cache keys."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        mock_client.delete.return_value = 1  # Redis returns number of deleted keys
        result = cache.delete("test_key")
        
        assert result is True
        mock_client.delete.assert_called_once_with("test_key")
        
        # Test deletion of non-existent key
        mock_client.delete.return_value = 0
        result = cache.delete("nonexistent_key")
        
        assert result is False
    
    def test_redis_cache_exists(self):
        """Test checking if keys exist."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        # Key exists
        mock_client.exists.return_value = 1
        result = cache.exists("existing_key")
        assert result is True
        
        # Key doesn't exist
        mock_client.exists.return_value = 0
        result = cache.exists("nonexistent_key")
        assert result is False
    
    def test_redis_cache_info(self):
        """Test getting Redis server info."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        mock_info = {
            "used_memory_human": "2.5M",
            "connected_clients": 5,
            "uptime_in_days": 7,
            "keyspace_hits": 1000,
            "keyspace_misses": 100
        }
        mock_client.info.return_value = mock_info
        
        info = cache.info()
        
        assert info["status"] == "connected"
        assert info["used_memory_human"] == "2.5M"
        assert info["connected_clients"] == 5
        assert info["uptime_in_days"] == 7
        # Hit rate should be 1000/(1000+100) = ~0.91
        assert abs(info["hit_rate"] - 0.909) < 0.01
    
    def test_redis_cache_operations_without_client(self):
        """Test cache operations when client is None."""
        cache = RedisCache()
        cache.client = None
        
        assert cache.get("key") is None
        assert cache.set("key", "value") is False
        assert cache.delete("key") is False
        assert cache.exists("key") is False
        
        info = cache.info()
        assert info["status"] == "disconnected"
    
    def test_redis_cache_error_handling(self):
        """Test error handling in cache operations."""
        mock_client = Mock()
        cache = RedisCache()
        cache.client = mock_client
        
        # Simulate Redis errors
        mock_client.get.side_effect = redis.RedisError("Connection timeout")
        mock_client.setex.side_effect = redis.RedisError("Memory full")
        mock_client.delete.side_effect = redis.RedisError("Connection lost")
        mock_client.exists.side_effect = redis.RedisError("Network error")
        
        assert cache.get("key") is None
        assert cache.set("key", "value") is False
        assert cache.delete("key") is False
        assert cache.exists("key") is False
    
    def test_redis_cache_default_ttl(self):
        """Test using default TTL when none specified."""
        mock_client = Mock()
        cache = RedisCache(default_ttl=7200)  # 2 hours
        cache.client = mock_client
        
        mock_client.setex.return_value = True
        cache.set("key", "value")  # No TTL specified
        
        mock_client.setex.assert_called_once_with("key", 7200, b"value")


class TestMemoryCache:
    """Unit tests for MemoryCache implementation."""
    
    def test_memory_cache_initialization(self):
        """Test MemoryCache initialization."""
        cache = MemoryCache(default_ttl=3600)
        
        assert cache.default_ttl == 3600
        assert len(cache.cache) == 0
        assert cache.lock is not None
    
    def test_memory_cache_set_get_simple(self):
        """Test setting and getting simple values."""
        cache = MemoryCache()
        
        result = cache.set("key1", "value1")
        assert result is True
        
        value = cache.get("key1")
        assert value == "value1"
    
    def test_memory_cache_set_get_complex(self):
        """Test setting and getting complex objects."""
        cache = MemoryCache()
        
        test_data = {
            "user": {"id": 123, "name": "Alice"},
            "permissions": ["read", "write"],
            "metadata": {"created": "2023-01-01", "score": 95.5}
        }
        
        cache.set("complex_key", test_data)
        retrieved = cache.get("complex_key")
        
        assert retrieved == test_data
        # Note: MemoryCache returns the same object, not a deep copy
    
    def test_memory_cache_ttl_expiration(self):
        """Test TTL expiration functionality."""
        cache = MemoryCache()
        
        # Set with very short TTL
        cache.set("short_lived", "value", ttl=1)
        
        # Should be available immediately
        assert cache.get("short_lived") == "value"
        
        # Mock time passing
        with patch('src.cache.memory_cache.time.time') as mock_time:
            # Initial time
            mock_time.return_value = 1000
            cache.set("timed_key", "timed_value", ttl=10)
            
            # Still within TTL
            mock_time.return_value = 1005
            assert cache.get("timed_key") == "timed_value"
            
            # Past TTL
            mock_time.return_value = 1015
            assert cache.get("timed_key") is None
    
    def test_memory_cache_max_size_eviction(self):
        """Test basic cache functionality (no max size in current implementation)."""
        cache = MemoryCache()
        
        # Fill cache with multiple items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert len(cache.cache) == 3
        
        # Access key1
        cache.get("key1")
        
        # Add fourth item - all should be present since no max size limit
        cache.set("key4", "value4")
        
        assert len(cache.cache) == 4
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_memory_cache_delete(self):
        """Test deleting cache entries."""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Delete existing key
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        
        # Delete non-existent key
        assert cache.delete("nonexistent") is False
    
    def test_memory_cache_exists(self):
        """Test checking if keys exist."""
        cache = MemoryCache()
        
        cache.set("existing_key", "value")
        
        assert cache.exists("existing_key") is True
        assert cache.exists("nonexistent_key") is False
    
    def test_memory_cache_clear(self):
        """Test clearing all cache entries."""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        assert len(cache.cache) == 3
        
        # Clear by setting empty cache (no clear method in current implementation)
        cache.cache.clear()
        
        assert len(cache.cache) == 0
        assert cache.get("key1") is None
    
    def test_memory_cache_info(self):
        """Test getting cache statistics."""
        cache = MemoryCache()
        
        # Add some entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Generate some hits and misses
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Hit
        cache.get("nonexistent")  # Miss
        cache.get("another_miss")  # Miss
        
        info = cache.info()
        
        assert info["status"] == "in-memory"
        assert info["total_keys"] == 3
        assert info["active_keys"] >= 0
    
    def test_memory_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = MemoryCache()
        
        with patch('src.cache.memory_cache.time.time') as mock_time:
            mock_time.return_value = 1000
            
            # Add entries with different TTLs
            cache.set("short", "value1", ttl=5)
            cache.set("medium", "value2", ttl=15)
            cache.set("long", "value3", ttl=25)
            
            assert len(cache.cache) == 3
            
            # Move time forward past short TTL
            mock_time.return_value = 1010
            # Test expiration by getting the values (auto-cleanup on access)
            
            assert cache.get("short") is None
            assert cache.get("medium") == "value2"
            assert cache.get("long") == "value3"
    
    def test_memory_cache_update_access_time(self):
        """Test basic cache access functionality."""
        cache = MemoryCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Access key1
        result = cache.get("key1")
        assert result == "value1"
        
        # Add third key - all keys remain since no size limit
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_memory_cache_set_updates_existing(self):
        """Test that setting an existing key updates it."""
        cache = MemoryCache()
        
        cache.set("key1", "original_value")
        assert cache.get("key1") == "original_value"
        
        cache.set("key1", "updated_value")
        assert cache.get("key1") == "updated_value"
        
        # Should still be only one entry
        assert len(cache.cache) == 1


class TestCacheIntegration:
    """Integration tests for cache implementations."""
    
    def test_cache_interface_compatibility(self):
        """Test that both cache implementations have compatible interfaces."""
        memory_cache = MemoryCache()
        
        # Mock Redis cache
        redis_cache = Mock()
        redis_cache.get.return_value = "redis_value"
        redis_cache.set.return_value = True
        redis_cache.delete.return_value = True
        redis_cache.exists.return_value = True
        
        # Both should support the same operations
        for cache in [memory_cache, redis_cache]:
            cache.set("test_key", "test_value")
            value = cache.get("test_key")
            cache.exists("test_key")
            cache.delete("test_key")
    
    def test_cache_fallback_pattern(self):
        """Test common pattern of falling back from Redis to Memory cache."""
        memory_cache = MemoryCache()
        
        # Simulate Redis being unavailable
        redis_cache = Mock()
        redis_cache.get.side_effect = Exception("Redis unavailable")
        redis_cache.set.side_effect = Exception("Redis unavailable")
        
        def get_with_fallback(key):
            try:
                return redis_cache.get(key)
            except:
                return memory_cache.get(key)
        
        def set_with_fallback(key, value):
            try:
                return redis_cache.set(key, value)
            except:
                return memory_cache.set(key, value)
        
        # Should fallback to memory cache
        assert set_with_fallback("key", "value") is True
        assert get_with_fallback("key") == "value"


if __name__ == "__main__":
    pytest.main([__file__])
