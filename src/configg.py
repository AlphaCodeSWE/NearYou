"""
Sistema di configurazione avanzato con supporto per diversi ambienti.
Carica configurazioni da file .env e supporta override con variabili d'ambiente.
"""
import os
import sys
import json
from enum import Enum
from typing import Any, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseSettings, Field, validator

# Definizione ambienti supportati
class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"

# Determina ambiente corrente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
if ENVIRONMENT not in [e.value for e in Environment]:
    ENVIRONMENT = Environment.DEVELOPMENT.value

# Determina percorso del file .env appropriato
env_file_path = os.getenv("ENV_FILE")

if not env_file_path:
    # Cerca il file .env in base all'ambiente
    if ENVIRONMENT == Environment.TEST.value:
        env_file_path = ".env.test"
    elif ENVIRONMENT == Environment.STAGING.value:
        env_file_path = ".env.staging"
    elif ENVIRONMENT == Environment.PRODUCTION.value:
        env_file_path = ".env.production"
    else:
        env_file_path = ".env"

# Carica il file .env
load_dotenv(dotenv_path=env_file_path)

# Modello di configurazione con validazione
class AppConfig(BaseSettings):
    """
    Configurazione applicazione con validazione e valori default.
    Utilizza Pydantic per validare i valori.
    """
    # Ambiente
    ENVIRONMENT: str = Field(ENVIRONMENT, env="ENVIRONMENT")
    DEBUG: bool = Field(ENVIRONMENT != Environment.PRODUCTION.value, env="DEBUG")
    
    # Configurazione Log
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Configurazione Kafka
    KAFKA_BROKER: str = Field("kafka:9093", env="KAFKA_BROKER")
    KAFKA_TOPIC: str = Field("gps_stream", env="KAFKA_TOPIC")
    CONSUMER_GROUP: str = Field("gps_consumers_group", env="CONSUMER_GROUP")
    
    # Configurazione SSL/TLS
    SSL_CAFILE: str = Field("/workspace/certs/ca.crt", env="SSL_CAFILE")
    SSL_CERTFILE: str = Field("/workspace/certs/client_cert.pem", env="SSL_CERTFILE")
    SSL_KEYFILE: str = Field("/workspace/certs/client_key.pem", env="SSL_KEYFILE")
    
    # Configurazione ClickHouse
    CLICKHOUSE_HOST: str = Field("clickhouse-server", env="CLICKHOUSE_HOST")
    CLICKHOUSE_USER: str = Field("default", env="CLICKHOUSE_USER")
    CLICKHOUSE_PASSWORD: str = Field("", env="CLICKHOUSE_PASSWORD")
    CLICKHOUSE_PORT: int = Field(9000, env="CLICKHOUSE_PORT")
    CLICKHOUSE_DATABASE: str = Field("nearyou", env="CLICKHOUSE_DATABASE")
    
    # Configurazione Postgres
    POSTGRES_HOST: str = Field("postgres-postgis", env="POSTGRES_HOST")
    POSTGRES_USER: str = Field("nearuser", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("near_you_shops", env="POSTGRES_DB")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    
    # URL dei microservizi
    MESSAGE_GENERATOR_URL: str = Field(
        "http://message-generator:8001/generate",
        env="MESSAGE_GENERATOR_URL",
    )
    
    # Configurazione JWT
    JWT_SECRET: str = Field("", env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_S: int = Field(3600, env="JWT_EXPIRATION_S")
    
    # Configurazione Google Maps
    GOOGLE_MAPS_API_KEY: str = Field("", env="GOOGLE_MAPS_API_KEY")
    
    # Configurazione OSRM
    OSRM_URL: str = Field("http://osrm-milano:5000", env="OSRM_URL")
    MILANO_MIN_LAT: float = Field(45.40, env="MILANO_MIN_LAT")
    MILANO_MAX_LAT: float = Field(45.50, env="MILANO_MAX_LAT")
    MILANO_MIN_LON: float = Field(9.10, env="MILANO_MIN_LON")
    MILANO_MAX_LON: float = Field(9.30, env="MILANO_MAX_LON")
    
    # Configurazione Redis Cache
    REDIS_HOST: str = Field("redis-cache", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    REDIS_PASSWORD: str = Field("", env="REDIS_PASSWORD")
    CACHE_TTL: int = Field(86400, env="CACHE_TTL")
    CACHE_ENABLED: bool = Field(True, env="CACHE_ENABLED")
    
    # Configurazione LLM
    LLM_PROVIDER: str = Field("groq", env="LLM_PROVIDER")
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    OPENAI_API_BASE: str = Field("", env="OPENAI_API_BASE")
    
    # Validatori
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Valida che il livello di log sia corretto."""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if v.upper() not in valid_levels:
            return "INFO"
        return v.upper()
    
    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v, values):
        """Valida che sia presente un JWT secret in produzione."""
        env = values.get("ENVIRONMENT")
        if env == Environment.PRODUCTION.value and not v:
            raise ValueError("JWT_SECRET è obbligatorio in ambiente di produzione")
        return v
    
    class Config:
        """Configurazione per Pydantic."""
        env_file = env_file_path
        case_sensitive = True

def load_config() -> AppConfig:
    """
    Carica la configurazione dell'applicazione.
    
    Returns:
        AppConfig: Istanza validata della configurazione
    """
    try:
        config = AppConfig()
        return config
    except Exception as e:
        sys.stderr.write(f"Errore caricamento configurazione: {str(e)}\n")
        sys.exit(1)

# Istanza globale della configurazione
config = load_config()

# Esporta tutte le configurazioni come variabili del modulo
ENVIRONMENT = config.ENVIRONMENT
DEBUG = config.DEBUG
LOG_LEVEL = config.LOG_LEVEL
KAFKA_BROKER = config.KAFKA_BROKER
KAFKA_TOPIC = config.KAFKA_TOPIC
CONSUMER_GROUP = config.CONSUMER_GROUP
SSL_CAFILE = config.SSL_CAFILE
SSL_CERTFILE = config.SSL_CERTFILE
SSL_KEYFILE = config.SSL_KEYFILE
CLICKHOUSE_HOST = config.CLICKHOUSE_HOST
CLICKHOUSE_USER = config.CLICKHOUSE_USER
CLICKHOUSE_PASSWORD = config.CLICKHOUSE_PASSWORD
CLICKHOUSE_PORT = config.CLICKHOUSE_PORT
CLICKHOUSE_DATABASE = config.CLICKHOUSE_DATABASE
POSTGRES_HOST = config.POSTGRES_HOST
POSTGRES_USER = config.POSTGRES_USER
POSTGRES_PASSWORD = config.POSTGRES_PASSWORD
POSTGRES_DB = config.POSTGRES_DB
POSTGRES_PORT = config.POSTGRES_PORT
MESSAGE_GENERATOR_URL = config.MESSAGE_GENERATOR_URL
JWT_SECRET = config.JWT_SECRET
JWT_ALGORITHM = config.JWT_ALGORITHM
JWT_EXPIRATION_S = config.JWT_EXPIRATION_S
GOOGLE_MAPS_API_KEY = config.GOOGLE_MAPS_API_KEY
OSRM_URL = config.OSRM_URL
MILANO_MIN_LAT = config.MILANO_MIN_LAT
MILANO_MAX_LAT = config.MILANO_MAX_LAT
MILANO_MIN_LON = config.MILANO_MIN_LON
MILANO_MAX_LON = config.MILANO_MAX_LON
REDIS_HOST = config.REDIS_HOST
REDIS_PORT = config.REDIS_PORT
REDIS_DB = config.REDIS_DB
REDIS_PASSWORD = config.REDIS_PASSWORD
CACHE_TTL = config.CACHE_TTL
CACHE_ENABLED = config.CACHE_ENABLED
LLM_PROVIDER = config.LLM_PROVIDER
OPENAI_API_KEY = config.OPENAI_API_KEY
OPENAI_API_BASE = config.OPENAI_API_BASE

# Funzione per esportare come dizionario
def get_config_dict() -> Dict[str, Any]:
    """
    Restituisce tutte le configurazioni come dizionario.
    
    Returns:
        Dict[str, Any]: Dictionary con tutte le configurazioni
    """
    return config.dict()

# Funzione per stampare la configurazione corrente (utile per debug)
def print_config(masked: bool = True):
    """
    Stampa la configurazione corrente.
    
    Args:
        masked: Se True, nasconde i valori sensibili
    """
    config_dict = get_config_dict()
    
    # Nascondi valori sensibili
    if masked:
        sensitive_keys = ["JWT_SECRET", "CLICKHOUSE_PASSWORD", "POSTGRES_PASSWORD", 
                          "REDIS_PASSWORD", "OPENAI_API_KEY"]
        for key in sensitive_keys:
            if key in config_dict and config_dict[key]:
                config_dict[key] = "********"
    
    print(json.dumps(config_dict, indent=2))

# Se eseguito direttamente, stampa la configurazione corrente
if __name__ == "__main__":
    print_config()