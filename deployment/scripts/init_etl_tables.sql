-- deployment/scripts/init_etl_tables.sql
-- Da eseguire dopo init_postgres.sh

-- Aggiungi tracking alle tabelle esistenti
ALTER TABLE shops ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE shops ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Tabella per tracciare i cambiamenti
CREATE TABLE IF NOT EXISTS shops_change_log (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(shop_id),
    change_type VARCHAR(20) NOT NULL, -- CREATE, UPDATE, DELETE
    change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_values JSONB,
    new_values JSONB
);

-- Indici per query veloci
CREATE INDEX IF NOT EXISTS idx_shops_updated ON shops(updated_at);
CREATE INDEX IF NOT EXISTS idx_shops_created ON shops(created_at);
CREATE INDEX IF NOT EXISTS idx_change_log_time ON shops_change_log(change_time);
CREATE INDEX IF NOT EXISTS idx_change_log_type ON shops_change_log(change_type);

-- Vista per analisi rapide
CREATE OR REPLACE VIEW daily_shop_changes AS
SELECT 
    DATE(change_time) as date,
    COUNT(*) FILTER (WHERE change_type = 'CREATE') as new_shops,
    COUNT(*) FILTER (WHERE change_type = 'UPDATE') as updated_shops,
    COUNT(*) as total_changes
FROM shops_change_log
GROUP BY DATE(change_time)
ORDER BY date DESC;