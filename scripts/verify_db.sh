#!/bin/bash
# Script per verificare il contenuto dei database

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== Verifica Database NearYou ===${NC}\n"

# Verifica ClickHouse
echo -e "${CYAN}1. ClickHouse - Database e Tabelle${NC}"
docker exec clickhouse clickhouse-client --query "SHOW DATABASES" | grep -q nearyou && \
    echo -e "${GREEN}✓ Database 'nearyou' presente${NC}" || \
    echo -e "${RED}✗ Database 'nearyou' non trovato${NC}"

echo -e "\n${CYAN}Tabelle in ClickHouse:${NC}"
docker exec clickhouse clickhouse-client --query "USE nearyou; SHOW TABLES;"

echo -e "\n${CYAN}Conteggio record:${NC}"
echo -n "  users: "
docker exec clickhouse clickhouse-client --query "SELECT COUNT(*) FROM nearyou.users" || echo "0"
echo -n "  user_events: "
docker exec clickhouse clickhouse-client --query "SELECT COUNT(*) FROM nearyou.user_events" || echo "0"

# Verifica PostgreSQL
echo -e "\n${CYAN}2. PostgreSQL - Database e Tabelle${NC}"
docker exec postgres psql -U nearyou -d nearyou_shops -c "\dt" | grep -q shops && \
    echo -e "${GREEN}✓ Tabella 'shops' presente${NC}" || \
    echo -e "${RED}✗ Tabella 'shops' non trovata${NC}"

echo -e "\n${CYAN}Conteggio shops:${NC}"
echo -n "  shops: "
docker exec postgres psql -U nearyou -d nearyou_shops -t -c "SELECT COUNT(*) FROM shops" | tr -d ' '

# Mostra alcuni dati di esempio
echo -e "\n${CYAN}3. Esempi di dati${NC}"
echo -e "\n${YELLOW}Ultimi 3 utenti:${NC}"
docker exec clickhouse clickhouse-client --query "SELECT user_id, username, age, profession FROM nearyou.users ORDER BY registration_time DESC LIMIT 3 FORMAT TabSeparated"

echo -e "\n${YELLOW}Ultimi 3 eventi:${NC}"
docker exec clickhouse clickhouse-client --query "SELECT event_time, user_id, poi_name, poi_info FROM nearyou.user_events ORDER BY event_time DESC LIMIT 3 FORMAT TabSeparated"

echo -e "\n${YELLOW}Primi 3 negozi:${NC}"
docker exec postgres psql -U nearyou -d nearyou_shops -t -c "SELECT shop_name, category FROM shops LIMIT 3"

echo -e "\n${GREEN}=== Verifica completata ===${NC}"