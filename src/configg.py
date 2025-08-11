# src/configg.py 
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Configura logger
logger = logging.getLogger(__name__)

class ConfigurationManager:
    """
    Singleton pattern implementation for configuration management.
    Ensures that only one configuration instance exists throughout the application.
    """
    _instance: Optional['ConfigurationManager'] = None
    _initialized = False
    
    def __new__(cls) -> 'ConfigurationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Prevent re-initialization
        if ConfigurationManager._initialized:
            return
        
        ConfigurationManager._initialized = True
        
        # Initialize all configuration values
        self._load_environment_config()
        
        # Validate critical configs in production/staging
        if self.environment in ["production", "staging"]:
            self.validate_critical_configs()
    
    def _load_environment_config(self):
        """Load all environment configurations."""
        # Identifica l'ambiente
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Configurazione Kafka
        self.kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9093")
        self.kafka_topic = os.getenv("KAFKA_TOPIC", "gps_stream")
        self.consumer_group = os.getenv("CONSUMER_GROUP", "gps_consumers_group")
        
        # Configurazione percorsi certificati
        self.ssl_cafile = os.getenv("SSL_CAFILE", "/workspace/certs/ca.crt")
        self.ssl_certfile = os.getenv("SSL_CERTFILE", "/workspace/certs/client_cert.pem")
        self.ssl_keyfile = os.getenv("SSL_KEYFILE", "/workspace/certs/client_key.pem")
        
        # Configurazione ClickHouse
        self.clickhouse_host = os.getenv("CLICKHOUSE_HOST", "clickhouse-server")
        self.clickhouse_user = os.getenv("CLICKHOUSE_USER", "default")
        self.clickhouse_password = os.getenv("CLICKHOUSE_PASSWORD", "pwe@123@l@")
        self.clickhouse_port = int(os.getenv("CLICKHOUSE_PORT", "9000"))
        self.clickhouse_database = os.getenv("CLICKHOUSE_DATABASE", "nearyou")
        
        # Configurazione Postgres
        self.postgres_host = os.getenv("POSTGRES_HOST", "postgres-postgis")
        self.postgres_user = os.getenv("POSTGRES_USER", "nearuser")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "nearypass")
        self.postgres_db = os.getenv("POSTGRES_DB", "near_you_shops")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        
        # URL del micro-servizio che genera i messaggi
        self.message_generator_url = os.getenv(
            "MESSAGE_GENERATOR_URL",
            "http://message-generator:8001/generate",
        )
        
        # —————— Configurazione JWT ——————
        self.jwt_secret = os.getenv(
            "JWT_SECRET",
            "9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a"
        )
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_s = int(os.getenv("JWT_EXPIRATION_S", "3600"))
        
        # Google Maps JS API Key
        self.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
        
        # Firebase App Check config
        self.firebase_api_key = os.getenv("FIREBASE_API_KEY", "")
        self.firebase_auth_domain = os.getenv("FIREBASE_AUTH_DOMAIN", "")
        self.firebase_project_id = os.getenv("FIREBASE_PROJECT_ID", "")
        self.firebase_recaptcha_site_key = os.getenv("FIREBASE_RECAPTCHA_SITE_KEY", "")
        
        # OSRM self-hosted per routing bici su Milano
        self.osrm_url = os.getenv("OSRM_URL", "http://osrm-milano:5000")
        self.milano_min_lat = float(os.getenv("MILANO_MIN_LAT", "45.40"))
        self.milano_max_lat = float(os.getenv("MILANO_MAX_LAT", "45.50"))
        self.milano_min_lon = float(os.getenv("MILANO_MIN_LON", "9.10"))
        self.milano_max_lon = float(os.getenv("MILANO_MAX_LON", "9.30"))
        
        # Config Redis cache
        self.redis_host = os.getenv("REDIS_HOST", "redis-cache")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.cache_ttl = int(os.getenv("CACHE_TTL", "86400"))
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "yes")
        
        # Config LLM
        self.llm_provider = os.getenv("LLM_PROVIDER", "groq")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_api_base = os.getenv("OPENAI_API_BASE", "")
    
    def get_clickhouse_config(self) -> Dict[str, Any]:
        """
        Ottiene configurazione per ClickHouse in formato adatto al client.
        Mantiene compatibilità con il codice esistente.
        """
        return {
            "host": self.clickhouse_host,
            "port": self.clickhouse_port,
            "user": self.clickhouse_user,
            "password": self.clickhouse_password,
            "database": self.clickhouse_database,
        }
    
    def get_postgres_uri(self) -> str:
        """Restituisce URI di connessione PostgreSQL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    def get_postgres_config(self) -> Dict[str, Any]:
        """Restituisce configurazione PostgreSQL come dictionary."""
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "database": self.postgres_db,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Restituisce configurazione Redis come dictionary."""
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": self.redis_password if self.redis_password else None,
            "default_ttl": self.cache_ttl,
        }
    
    def validate_critical_configs(self) -> None:
        """Valida configurazioni critiche e registra avvisi."""
        # Controlla JWT in produzione
        if self.environment == "production" and self.jwt_secret == "9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a":
            logger.warning(" SECURITY RISK: JWT_SECRET è impostato sul valore predefinito in produzione!")
        
        # Verifica configurazione ClickHouse
        if not self.clickhouse_host:
            logger.error("Manca configurazione CLICKHOUSE_HOST!")
        
        # Verifica configurazione Postgres
        if not self.postgres_host:
            logger.error("Manca configurazione POSTGRES_HOST!")

# Create singleton instance
config = ConfigurationManager()

# Backward compatibility - expose as module-level variables
ENVIRONMENT = config.environment

# -------------------- CONFIGURAZIONI ------------------

# Configurazione Kafka
KAFKA_BROKER = config.kafka_broker
KAFKA_TOPIC = config.kafka_topic
CONSUMER_GROUP = config.consumer_group

# Configurazione percorsi certificati
SSL_CAFILE = config.ssl_cafile
SSL_CERTFILE = config.ssl_certfile
SSL_KEYFILE = config.ssl_keyfile

# Configurazione ClickHouse
CLICKHOUSE_HOST = config.clickhouse_host
CLICKHOUSE_USER = config.clickhouse_user
CLICKHOUSE_PASSWORD = config.clickhouse_password
CLICKHOUSE_PORT = config.clickhouse_port
CLICKHOUSE_DATABASE = config.clickhouse_database

# Configurazione Postgres
POSTGRES_HOST = config.postgres_host
POSTGRES_USER = config.postgres_user
POSTGRES_PASSWORD = config.postgres_password
POSTGRES_DB = config.postgres_db
POSTGRES_PORT = config.postgres_port

# URL del micro-servizio che genera i messaggi
MESSAGE_GENERATOR_URL = config.message_generator_url

# —————— Configurazione JWT ——————
JWT_SECRET = config.jwt_secret
JWT_ALGORITHM = config.jwt_algorithm
JWT_EXPIRATION_S = config.jwt_expiration_s

# Google Maps JS API Key
GOOGLE_MAPS_API_KEY = config.google_maps_api_key

# Firebase App Check config
FIREBASE_API_KEY = config.firebase_api_key
FIREBASE_AUTH_DOMAIN = config.firebase_auth_domain
FIREBASE_PROJECT_ID = config.firebase_project_id
FIREBASE_RECAPTCHA_SITE_KEY = config.firebase_recaptcha_site_key

# OSRM self-hosted per routing bici su Milano
OSRM_URL = config.osrm_url
MILANO_MIN_LAT = config.milano_min_lat
MILANO_MAX_LAT = config.milano_max_lat
MILANO_MIN_LON = config.milano_min_lon
MILANO_MAX_LON = config.milano_max_lon

# Config Redis cache
REDIS_HOST = config.redis_host
REDIS_PORT = config.redis_port
REDIS_DB = config.redis_db
REDIS_PASSWORD = config.redis_password
CACHE_TTL = config.cache_ttl
CACHE_ENABLED = config.cache_enabled

# Config LLM
LLM_PROVIDER = config.llm_provider
OPENAI_API_KEY = config.openai_api_key
OPENAI_API_BASE = config.openai_api_base

# -------------------- FUNZIONI HELPER ------------------

def get_clickhouse_config() -> Dict[str, Any]:
    """
    Ottiene configurazione per ClickHouse in formato adatto al client.
    Mantiene compatibilità con il codice esistente.
    """
    return config.get_clickhouse_config()

def get_postgres_uri() -> str:
    """Restituisce URI di connessione PostgreSQL."""
    return config.get_postgres_uri()

def validate_critical_configs() -> None:
    """Valida configurazioni critiche e registra avvisi."""
    return config.validate_critical_configs()

# Expose singleton instance for direct access
def get_config() -> ConfigurationManager:
    """Get the singleton configuration instance."""
    return config