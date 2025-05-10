#!/bin/bash
# Script per inizializzare Airflow

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${CYAN}Inizializzazione Airflow...${NC}"

# Inizializza database Airflow
docker exec -i airflow-webserver airflow db init

# Crea utente admin
docker exec -i airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

echo -e "${GREEN}✓ Airflow inizializzato con successo${NC}"
echo -e "${CYAN}Credenziali Airflow: admin/admin${NC}"