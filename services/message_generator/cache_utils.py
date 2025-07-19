"""
Utilities per la gestione della cache dei messaggi.
"""
import logging
import hashlib
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache in-memory semplice (per produzione usare Redis)
_message_cache = {}
_cache_stats = {"hits": 0, "misses": 0}

def get_cached_message(cache_key: str) -> Optional[str]:
    """
    Recupera un messaggio dalla cache usando la chiave fornita.
    
    Args:
        cache_key: Chiave cache
        
    Returns:
        Optional[str]: Messaggio cachato o None se non presente
    """
    if cache_key in _message_cache:
        _cache_stats["hits"] += 1
        logger.debug(f"Cache HIT per chiave: {cache_key}")
        return _message_cache[cache_key]
    
    _cache_stats["misses"] += 1
    logger.debug(f"Cache MISS per chiave: {cache_key}")
    return None

def cache_message(cache_key: str, message: str) -> None:
    """
    Salva un messaggio nella cache.
    
    Args:
        cache_key: Chiave cache
        message: Messaggio da salvare
    """
    # Limite dimensione cache (evita memory leak)
    if len(_message_cache) > 1000:
        # Rimuovi il 20% dei messaggi più vecchi
        keys_to_remove = list(_message_cache.keys())[:200]
        for key in keys_to_remove:
            del _message_cache[key]
        logger.info("Cache pulita: rimossi 200 messaggi vecchi")
    
    _message_cache[cache_key] = message
    logger.debug(f"Messaggio salvato in cache per chiave: {cache_key}")

def get_cache_stats() -> Dict[str, Any]:
    """
    Restituisce statistiche della cache.
    
    Returns:
        Dict: Statistiche cache
    """
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (_cache_stats["hits"] / total * 100) if total > 0 else 0.0
    
    return {
        "enabled": True,
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "total": total,
        "hit_rate": round(hit_rate, 2),
        "cache_size": len(_message_cache),
        "cache_info": {
            "type": "in_memory",
            "max_size": 1000,
            "current_size": len(_message_cache)
        }
    }

def clear_cache() -> int:
    """
    Pulisce completamente la cache.
    
    Returns:
        int: Numero di messaggi rimossi
    """
    count = len(_message_cache)
    _message_cache.clear()
    _cache_stats["hits"] = 0
    _cache_stats["misses"] = 0
    logger.info(f"Cache completamente pulita: {count} messaggi rimossi")
    return count

# Funzioni di compatibilità per backward compatibility
def create_cache_key(user_params: Dict[str, Any], poi_params: Dict[str, Any]) -> str:
    """
    Crea chiave cache dai parametri (funzione di compatibilità).
    
    Args:
        user_params: Parametri utente
        poi_params: Parametri POI
        
    Returns:
        str: Chiave cache
    """
    cache_data = {
        'age': user_params.get('age'),
        'profession': user_params.get('profession', '').lower(),
        'interests': user_params.get('interests', '').lower(),
        'poi_name': poi_params.get('name', '').lower(),
        'poi_category': poi_params.get('category', '').lower()
    }
    
    cache_string = str(sorted(cache_data.items()))
    return hashlib.md5(cache_string.encode()).hexdigest()

# Alias per backward compatibility se necessario
def get_cached_message_legacy(user_params: Dict[str, Any], poi_params: Dict[str, Any]) -> Optional[str]:
    """
    Versione legacy che accetta user_params e poi_params separati.
    
    Args:
        user_params: Parametri utente
        poi_params: Parametri POI
        
    Returns:
        Optional[str]: Messaggio cachato o None
    """
    cache_key = create_cache_key(user_params, poi_params)
    return get_cached_message(cache_key)

def cache_message_legacy(user_params: Dict[str, Any], poi_params: Dict[str, Any], message: str) -> None:
    """
    Versione legacy per salvare messaggio.
    
    Args:
        user_params: Parametri utente
        poi_params: Parametri POI
        message: Messaggio da salvare
    """
    cache_key = create_cache_key(user_params, poi_params)
    cache_message(cache_key, message)