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

echo "Postgres è pronto. Procedo con la creazione delle tabelle..."

psql -h postgres -U nearuser -d near_you_shops <<'EOF'

-- Creazione tabella shops
CREATE TABLE IF NOT EXISTS shops (
    shop_id SERIAL PRIMARY KEY,
    shop_name VARCHAR(255),
    address TEXT,
    category VARCHAR(100),
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Creazione tabella offers
CREATE TABLE IF NOT EXISTS offers (
    offer_id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(shop_id) ON DELETE CASCADE,
    
    -- Dettagli offerta
    discount_percent INTEGER NOT NULL CHECK (discount_percent > 0 AND discount_percent <= 50),
    description TEXT NOT NULL,
    offer_type VARCHAR(20) DEFAULT 'percentage' CHECK (offer_type IN ('percentage', 'fixed_amount', 'buy_one_get_one')),
    
    -- Validità temporale
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_until DATE NOT NULL,
    
    -- Stato e metadati
    is_active BOOLEAN DEFAULT true,
    max_uses INTEGER DEFAULT NULL,
    current_uses INTEGER DEFAULT 0,
    
    -- Targeting
    min_age INTEGER DEFAULT NULL,
    max_age INTEGER DEFAULT NULL,
    target_categories TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per performance offers
CREATE INDEX IF NOT EXISTS idx_offers_shop_active ON offers(shop_id, is_active);
CREATE INDEX IF NOT EXISTS idx_offers_validity ON offers(valid_from, valid_until) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_offers_discount ON offers(discount_percent) WHERE is_active = true;

-- Trigger per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_offers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_offers_updated_at
    BEFORE UPDATE ON offers
    FOR EACH ROW
    EXECUTE FUNCTION update_offers_updated_at();

-- Constraint per validità date
ALTER TABLE offers ADD CONSTRAINT IF NOT EXISTS chk_offers_valid_dates 
    CHECK (valid_until > valid_from);

-- Commenti per documentazione
COMMENT ON TABLE offers IS 'Offerte e promozioni disponibili per i negozi';
COMMENT ON COLUMN offers.discount_percent IS 'Percentuale di sconto (1-50)';
COMMENT ON COLUMN offers.target_categories IS 'Array di categorie di interesse per targeting utenti';
COMMENT ON COLUMN offers.max_uses IS 'Numero massimo utilizzi (NULL = illimitato)';

EOF

echo "Tabelle shops e offers create con successo."
echo "Inizializzazione di PostGIS completata."