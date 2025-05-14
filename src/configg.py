# src/configg.py 
import os
import sys
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv
import logging

# Definizione degli ambienti supportati
class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

# Carica il file .env appropriato in base all'ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", Environment.DEVELOPMENT)

# Carica .env dalla directory corrente
load_dotenv()

# Carica file .env specifico per ambiente se esiste
env_file = Path(f".env.{ENVIRONMENT}")
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    
logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Eccezione sollevata per errori di validazione della configurazione."""
    pass

class ConfigBase:
    """Classe base per configurazioni con validazione."""
    
    # Set di parametri obbligatori da sovrascrivere nelle classi figlie
    REQUIRED_PARAMS: Set[str] = set()
    
    @classmethod
    def validate(cls):
        """Valida che tutti i parametri obbligatori siano impostati."""
        missing = []
        for param in cls.REQUIRED_PARAMS:
            value = getattr(cls, param, None)
            if value is None or value == "":
                missing.append(param)
        
        if missing:
            error_msg = f"Parametri di configurazione mancanti in {cls.__name__}: {', '.join(missing)}"
            logger.error(error_msg)
            if ENVIRONMENT in [Environment.STAGING, Environment.PRODUCTION]:
                raise ConfigValidationError(error_msg)
            else:
                logger.warning("Continuazione nonostante parametri mancanti perché non in produzione")

class KafkaConfig(ConfigBase):
    """Configurazione per Kafka."""
    
    REQUIRED_PARAMS = {"BROKER", "TOPIC"}
    
    BROKER = os.getenv("KAFKA_BROKER", "kafka:9093")
    TOPIC = os.getenv("KAFKA_TOPIC", "gps_stream")
    CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "gps_consumers_group")
    
    # Configurazione SSL
    SSL_ENABLED = ENVIRONMENT in [Environment.STAGING, Environment.PRODUCTION]
    SSL_CAFILE = os.getenv("SSL_CAFILE", "/workspace/certs/ca.crt")
    SSL_CERTFILE = os.getenv("SSL_CERTFILE", "/workspace/certs/client_cert.pem")
    SSL_KEYFILE = os.getenv("SSL_KEYFILE", "/workspace/certs/client_key.pem")
    
    @classmethod
    def get_producer_config(cls) -> Dict[str, Any]:
        """Restituisce configurazione per il producer Kafka."""
        config = {
            "bootstrap_servers": [cls.BROKER],
        }
        
        if cls.SSL_ENABLED:
            config.update({
                "security_protocol": "SSL",
                "ssl_cafile": cls.SSL_CAFILE,
                "ssl_certfile": cls.SSL_CERTFILE,
                "ssl_keyfile": cls.SSL_KEYFILE,
            })
            
        return config

class DatabaseConfig(ConfigBase):
    """Configurazione per database."""
    
    class ClickHouse(ConfigBase):
        """Configurazione per ClickHouse."""
        
        REQUIRED_PARAMS = {"HOST"}
        
        HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse-server")
        PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
        USER = os.getenv("CLICKHOUSE_USER", "default")
        PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "pwe@123@l@")
        DATABASE = os.getenv("CLICKHOUSE_DATABASE", "nearyou")
        
        @classmethod
        def get_connection_params(cls) -> Dict[str, Any]:
            """Restituisce parametri di connessione per ClickHouse."""
            return {
                "host": cls.HOST,
                "port": cls.PORT,
                "user": cls.USER,
                "password": cls.PASSWORD,
                "database": cls.DATABASE,
            }
    
    class Postgres(ConfigBase):
        """Configurazione per PostgreSQL."""
        
        REQUIRED_PARAMS = {"HOST", "DB"}
        
        HOST = os.getenv("POSTGRES_HOST", "postgres-postgis")
        PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        USER = os.getenv("POSTGRES_USER", "nearuser")
        PASSWORD = os.getenv("POSTGRES_PASSWORD", "nearypass")
        DB = os.getenv("POSTGRES_DB", "near_you_shops")
        
        @classmethod
        def get_connection_string(cls) -> str:
            """Restituisce connection string per PostgreSQL."""
            return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DB}"
        
        @classmethod
        def get_async_connection_params(cls) -> Dict[str, Any]:
            """Restituisce parametri di connessione per asyncpg."""
            return {
                "host": cls.HOST,
                "port": cls.PORT,
                "user": cls.USER,
                "password": cls.PASSWORD,
                "database": cls.DB,
            }

class ServicesConfig(ConfigBase):
    """Configurazione per servizi esterni."""
    
    # URL del servizio di generazione messaggi
    MESSAGE_GENERATOR_URL = os.getenv(
        "MESSAGE_GENERATOR_URL",
        "http://message-generator:8001/generate",
    )
    
    # OSRM per routing
    OSRM_URL = os.getenv("OSRM_URL", "http://osrm-milano:5000")
    MILANO_MIN_LAT = float(os.getenv("MILANO_MIN_LAT", "45.40"))
    MILANO_MAX_LAT = float(os.getenv("MILANO_MAX_LAT", "45.50"))
    MILANO_MIN_LON = float(os.getenv("MILANO_MIN_LON", "9.10"))
    MILANO_MAX_LON = float(os.getenv("MILANO_MAX_LON", "9.30"))

class CacheConfig(ConfigBase):
    """Configurazione per cache."""
    
    ENABLED = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
    TTL = int(os.getenv("CACHE_TTL", "86400"))
    
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    
    @classmethod
    def get_redis_params(cls) -> Dict[str, Any]:
        """Restituisce parametri di connessione per Redis."""
        params = {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB,
        }
        
        if cls.REDIS_PASSWORD:
            params["password"] = cls.REDIS_PASSWORD
            
        return params

class SecurityConfig(ConfigBase):
    """Configurazione per sicurezza e autenticazione."""
    
    REQUIRED_PARAMS = {"JWT_SECRET"}
    
    # JWT
    JWT_SECRET = os.getenv(
        "JWT_SECRET",
        "9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a"
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_S = int(os.getenv("JWT_EXPIRATION_S", "3600"))
    
    # Avvisa se la chiave JWT è quella predefinita in produzione
    @classmethod
    def validate(cls):
        super().validate()
        if ENVIRONMENT == Environment.PRODUCTION and cls.JWT_SECRET == "9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a":
            logger.warning("⚠️ SECURITY RISK: Usando JWT_SECRET predefinito in produzione!")

class AIConfig(ConfigBase):
    """Configurazione per AI e LLM."""
    
    # LLM
    PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    API_KEY = os.getenv("OPENAI_API_KEY", "")
    API_BASE = os.getenv("OPENAI_API_BASE", "")
    
    @classmethod
    def get_model_name(cls) -> str:
        """Restituisce il nome del modello appropriato per il provider scelto."""
        if cls.PROVIDER == "openai":
            return "gpt-4o-mini"
        elif cls.PROVIDER == "groq":
            return "gemma2-9b-it"
        else:
            return "gpt-3.5-turbo"  # Default fallback

# Valida le configurazioni all'importazione del modulo
def validate_all_configs():
    """Valida tutte le configurazioni."""
    configs = [
        KafkaConfig,
        DatabaseConfig.ClickHouse,
        DatabaseConfig.Postgres,
        SecurityConfig,
    ]
    
    for config in configs:
        config.validate()

# Valida solo in ambienti di staging o produzione
if ENVIRONMENT in [Environment.STAGING, Environment.PRODUCTION]:
    validate_all_configs()