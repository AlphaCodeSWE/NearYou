from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol
import logging

from .redis_cache import RedisCache
from .memory_cache import MemoryCache

logger = logging.getLogger(__name__)

class CacheInterface(Protocol):
    """Protocol defining the cache interface."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        ...
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        ...
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    def info(self) -> Dict[str, Any]:
        """Get cache info."""
        ...

class CacheFactory:
    """
    Factory pattern implementation for cache creation.
    Creates appropriate cache instances based on configuration.
    """
    
    @staticmethod
    def create_cache(cache_type: str = "auto", **config) -> CacheInterface:
        """
        Create cache instance based on type and configuration.
        
        Args:
            cache_type: Type of cache ('redis', 'memory', 'auto')
            **config: Configuration parameters
            
        Returns:
            CacheInterface: Cache instance
        """
        if cache_type == "memory":
            return CacheFactory._create_memory_cache(**config)
        elif cache_type == "redis":
            return CacheFactory._create_redis_cache(**config)
        elif cache_type == "auto":
            return CacheFactory._create_auto_cache(**config)
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")
    
    @staticmethod
    def _create_memory_cache(**config) -> MemoryCache:
        """Create memory cache instance."""
        default_ttl = config.get("default_ttl", 86400)
        logger.info("Creating MemoryCache instance")
        return MemoryCache(default_ttl=default_ttl)
    
    @staticmethod
    def _create_redis_cache(**config) -> RedisCache:
        """Create Redis cache instance."""
        logger.info("Creating RedisCache instance")
        return RedisCache(
            host=config.get("host", "localhost"),
            port=config.get("port", 6379),
            db=config.get("db", 0),
            password=config.get("password"),
            default_ttl=config.get("default_ttl", 86400)
        )
    
    @staticmethod
    def _create_auto_cache(**config) -> CacheInterface:
        """
        Automatically choose cache type based on availability.
        Try Redis first, fallback to memory cache.
        """
        try:
            # Try to create Redis cache first
            redis_cache = CacheFactory._create_redis_cache(**config)
            # Test connection
            redis_cache.set("__test__", "connection_test", ttl=1)
            redis_cache.delete("__test__")
            logger.info("Auto-selected RedisCache (connection successful)")
            return redis_cache
        except Exception as e:
            logger.warning(f"Redis not available ({e}), falling back to MemoryCache")
            return CacheFactory._create_memory_cache(**config)

# Singleton Cache Manager
class CacheManager:
    """
    Singleton pattern implementation for cache management.
    Ensures single cache instance throughout the application.
    """
    _instance: Optional['CacheManager'] = None
    _cache: Optional[CacheInterface] = None
    
    def __new__(cls) -> 'CacheManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, cache_type: str = "auto", **config) -> None:
        """Initialize cache with given configuration."""
        if self._cache is None:
            self._cache = CacheFactory.create_cache(cache_type, **config)
            logger.info(f"Cache manager initialized with {type(self._cache).__name__}")
    
    def get_cache(self) -> CacheInterface:
        """Get the cache instance."""
        if self._cache is None:
            raise RuntimeError("Cache not initialized. Call initialize() first.")
        return self._cache
    
    def reset(self) -> None:
        """Reset cache instance (mainly for testing)."""
        self._cache = None

# Create singleton instance
cache_manager = CacheManager()

def get_cache() -> CacheInterface:
    """Get the singleton cache instance."""
    return cache_manager.get_cache()

def initialize_cache(cache_type: str = "auto", **config) -> None:
    """Initialize the singleton cache with configuration."""
    cache_manager.initialize(cache_type, **config)

__all__ = [
    'RedisCache', 
    'MemoryCache', 
    'CacheFactory', 
    'CacheManager', 
    'CacheInterface',
    'get_cache',
    'initialize_cache',
    'cache_manager'
]