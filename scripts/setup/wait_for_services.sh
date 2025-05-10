#!/bin/bash
# Script per attendere che tutti i servizi siano pronti

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Funzione per controllare se un servizio è pronto
check_service() {
    local service=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${CYAN}Controllo $service...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo -e "${GREEN}✓ $service pronto${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}  Tentativo $attempt/$max_attempts...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}✗ $service non disponibile dopo $max_attempts tentativi${NC}"
    return 1
}

# Controlla tutti i servizi principali
check_service "PostgreSQL" 5432
check_service "ClickHouse" 9000
check_service "Kafka" 9093
check_service "Redis" 6379
check_service "OSRM" 5000

echo -e "${GREEN}✓ Tutti i servizi sono pronti!${NC}"