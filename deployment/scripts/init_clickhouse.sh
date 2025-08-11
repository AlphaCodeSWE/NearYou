#!/bin/bash
set -e

echo "--- Inizio script di inizializzazione ---"
echo "Working directory: $(pwd)"
echo "Elenco dei file nella directory:"
ls -l

echo "Attesa che ClickHouse sia pronto..."

until docker exec -i clickhouse-server clickhouse-client --query "SELECT 1" >/dev/null 2>&1; do
    echo "ClickHouse non è ancora pronto, attendo 5 secondi..."
    sleep 5
done

echo "ClickHouse è pronto. Procedo con la creazione."

# Creazione del database se non esiste
echo "Creazione del database 'nearyou' (se non esiste già)..."
docker exec -i clickhouse-server clickhouse-client --query "CREATE DATABASE IF NOT EXISTS nearyou;"

# Creazione della tabella users con deduplicazione
echo "Creazione della tabella users..."
docker exec -i clickhouse-server clickhouse-client --query "
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
    ) ENGINE = ReplacingMergeTree()
    ORDER BY user_id;
"

# Creazione tabella staging per filtraggio duplicati
echo "Creazione della tabella temporanea users_staging..."
docker exec -i clickhouse-server clickhouse-client --query "
    USE nearyou;
    CREATE TABLE IF NOT EXISTS users_staging AS users
    ENGINE = Memory;
"

# Creazione della tabella user_events
echo "Creazione della tabella user_events..."
docker exec -i clickhouse-server clickhouse-client --query "
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

# Creazione della tabella user_visits
echo "Creazione della tabella user_visits..."
docker exec -i clickhouse-server clickhouse-client --query "
    USE nearyou;
    CREATE TABLE IF NOT EXISTS user_visits (
        visit_id UInt64,
        
        -- Identificatori
        user_id UInt64,
        shop_id UInt64,
        offer_id UInt64 DEFAULT 0,
        
        -- Timing della visita
        visit_start_time DateTime,
        visit_end_time DateTime DEFAULT toDateTime(0),
        duration_minutes UInt32 DEFAULT 0,
        
        -- Dettagli comportamento
        offer_accepted Boolean DEFAULT false,
        estimated_spending Float32 DEFAULT 0.0,
        user_satisfaction UInt8 DEFAULT 5,
        
        -- Contesto
        day_of_week UInt8 DEFAULT toDayOfWeek(visit_start_time),
        hour_of_day UInt8 DEFAULT toHour(visit_start_time),
        weather_condition String DEFAULT '',
        
        -- Dati utente snapshot
        user_age UInt8 DEFAULT 0,
        user_profession String DEFAULT '',
        user_interests String DEFAULT '',
        
        -- Dati negozio snapshot  
        shop_name String DEFAULT '',
        shop_category String DEFAULT '',
        
        -- Metadati
        created_at DateTime DEFAULT now()
        
    ) ENGINE = MergeTree()
    PARTITION BY toYYYYMM(visit_start_time)
    ORDER BY (user_id, visit_start_time, shop_id)
    SETTINGS index_granularity = 8192;
"

# Creazione tabella aggregata per statistiche
echo "Creazione della tabella user_visits_by_shop..."
docker exec -i clickhouse-server clickhouse-client --query "
    USE nearyou;
    CREATE TABLE IF NOT EXISTS user_visits_by_shop (
        shop_id UInt64,
        visit_date Date,
        total_visits UInt32,
        total_duration_minutes UInt64,
        offers_accepted UInt32,
        avg_satisfaction Float32,
        total_revenue Float32
    ) ENGINE = SummingMergeTree(total_visits, total_duration_minutes, offers_accepted, total_revenue)
    PARTITION BY toYYYYMM(visit_date)
    ORDER BY (shop_id, visit_date);
"

# Creazione vista materializzata per statistiche real-time
echo "Creazione vista materializzata mv_daily_shop_stats..."
docker exec -i clickhouse-server clickhouse-client --query "
    USE nearyou;
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_shop_stats
    TO user_visits_by_shop
    AS SELECT
        shop_id,
        toDate(visit_start_time) as visit_date,
        count() as total_visits,
        sum(duration_minutes) as total_duration_minutes,
        countIf(offer_accepted) as offers_accepted,
        avg(user_satisfaction) as avg_satisfaction,
        sum(estimated_spending) as total_revenue
    FROM user_visits
    GROUP BY shop_id, visit_date;
"

echo "Inizializzazione di ClickHouse completata."

echo ""
echo "[!] Per inserire dati evitando duplicati su user_id:"
echo "docker exec -i clickhouse-server clickhouse-client --query \"INSERT INTO nearyou.users SELECT DISTINCT * FROM nearyou.users_staging;\""
echo "Poi svuota la staging table con:"
echo "docker exec -i clickhouse-server clickhouse-client --query \"TRUNCATE TABLE nearyou.users_staging;\""
