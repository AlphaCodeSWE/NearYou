#!/bin/bash
# Script per controllare lo stato di salute dei servizi

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}Controllo salute servizi...${NC}"

# Funzione per controllare un servizio
check_service() {
    local service=$1
    local check_command=$2
    
    echo -n "  $service: "
    if eval $check_command &>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${RED}✗ ERRORE${NC}"
    fi
}

# Controlla tutti i servizi
check_service "PostgreSQL" "docker exec postgres pg_isready -U nearyou"
check_service "ClickHouse" "docker exec clickhouse clickhouse-client --query 'SELECT 1'"
check_service "Kafka" "docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9093"
check_service "Redis" "docker exec redis redis-cli -a development ping"
check_service "Grafana" "curl -s http://localhost:3000/api/health"
check_service "Airflow" "curl -s http://localhost:8080/health"
check_service "Dashboard" "curl -s http://localhost:8003/"
check_service "Message Generator" "curl -s http://localhost:8001/health"

echo -e "\n${GREEN}Controllo completato${NC}"