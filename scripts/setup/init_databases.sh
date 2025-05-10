#!/bin/bash
# Script per inizializzare i database

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}Inizializzazione database...${NC}"

# Inizializza ClickHouse
echo -e "${CYAN}Inizializzazione ClickHouse...${NC}"
docker exec -i clickhouse clickhouse-client --query "CREATE DATABASE IF NOT EXISTS nearyou;"

docker exec -i clickhouse clickhouse-client --query "
    USE nearyou;
    CREATE TABLE IF NOT EXISTS users (
        user_id           UInt64,
        username          String,
        full_name         String,
        email             String,
        phone_number      String,
        password          String,
        user_type         String,
        gender            String,
        age               UInt32,
        profession        String,
        interests         String,
        country           String,
        city              String,
        registration_time DateTime
    ) ENGINE = MergeTree()
    ORDER BY user_id;
"

docker exec -i clickhouse clickhouse-client --query "
    USE nearyou;
    CREATE TABLE IF NOT EXISTS user_events (
        event_id   UInt64,
        event_time DateTime,
        user_id    UInt64,
        latitude   Float64,
        longitude  Float64,
        poi_range  Float64,
        poi_name   String,
        poi_info   String
    ) ENGINE = MergeTree()
    ORDER BY event_id;
"
echo -e "${GREEN}✓ ClickHouse inizializzato${NC}"

# Inizializza PostgreSQL
echo -e "${CYAN}Inizializzazione PostgreSQL...${NC}"
docker exec -i postgres psql -U nearyou -d nearyou_shops -c "
CREATE TABLE IF NOT EXISTS shops (
    shop_id SERIAL PRIMARY KEY,
    shop_name VARCHAR(255),
    address TEXT,
    category VARCHAR(100),
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"
echo -e "${GREEN}✓ PostgreSQL inizializzato${NC}"

echo -e "${GREEN}✓ Database inizializzati con successo${NC}"