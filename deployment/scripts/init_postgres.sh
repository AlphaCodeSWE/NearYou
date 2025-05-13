#!/bin/bash
set -xe

echo "--- Inizio script di inizializzazione per PostGIS ---"
echo "Working directory: $(pwd)"
echo "Elenco dei file nella directory:"
ls -l

echo "Attesa iniziale di 60 secondi per il setup di Postgres..."
sleep 60

echo "Attesa che Postgres con PostGIS sia pronto..."

# Imposta la password per psql
export PGPASSWORD=nearypass

COUNTER=0
MAX_RETRIES=40

while true; do
    output=$(psql -h postgres -U nearuser -d near_you_shops -c "SELECT 1" 2>&1) && break
    echo "Tentativo $(($COUNTER+1)): psql non è ancora riuscito. Errore: $output"
    sleep 15
    COUNTER=$(($COUNTER+1))
    if [ $COUNTER -ge $MAX_RETRIES ]; then
         echo "Limite massimo di tentativi raggiunto. Uscita."
         exit 1
    fi
done

echo "Postgres è pronto. Procedo con la creazione della tabella shops..."

psql -h postgres -U nearuser -d near_you_shops <<'EOF'
CREATE TABLE IF NOT EXISTS shops (
    shop_id SERIAL PRIMARY KEY,
    shop_name VARCHAR(255),
    address TEXT,
    category VARCHAR(100),
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

echo "Inizializzazione di PostGIS completata."