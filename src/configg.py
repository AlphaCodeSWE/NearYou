# src/configg.py - 
import os
from dotenv import load_dotenv

# Carica le variabili dall'ambiente
load_dotenv()

# Configurazione Kafka
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9093")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "gps_stream")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "gps_consumers_group")

# Configurazione percorsi certificati
SSL_CAFILE = os.getenv("SSL_CAFILE", "/workspace/certs/ca.crt")
SSL_CERTFILE = os.getenv("SSL_CERTFILE", "/workspace/certs/client_cert.pem")
SSL_KEYFILE = os.getenv("SSL_KEYFILE", "/workspace/certs/client_key.pem")

# Configurazione ClickHouse
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse-server")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "pwe@123@l@")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "nearyou")

# Configurazione Postgres
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-postgis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "nearuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "nearypass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "near_you_shops")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))

# URL del micro-servizio che genera i messaggi
MESSAGE_GENERATOR_URL = os.getenv(
    "MESSAGE_GENERATOR_URL",
    "http://message-generator:8001/generate",
)

# —————— Configurazione JWT ——————
JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "9f8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_S = int(os.getenv("JWT_EXPIRATION_S", "3600"))

# Google Maps JS API Key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Firebase App Check config
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN", "")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_RECAPTCHA_SITE_KEY = os.getenv("FIREBASE_RECAPTCHA_SITE_KEY", "")

# OSRM self-hosted per routing bici su Milano
OSRM_URL = os.getenv("OSRM_URL", "http://osrm-milano:5000")
MILANO_MIN_LAT = float(os.getenv("MILANO_MIN_LAT", "45.40"))
MILANO_MAX_LAT = float(os.getenv("MILANO_MAX_LAT", "45.50"))
MILANO_MIN_LON = float(os.getenv("MILANO_MIN_LON", "9.10"))
MILANO_MAX_LON = float(os.getenv("MILANO_MAX_LON", "9.30"))

# Config Redis cache
REDIS_HOST = os.getenv("REDIS_HOST", "redis-cache")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() in ("true", "1", "yes")

# Config LLM
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")