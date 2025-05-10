#!/bin/bash
# Script di inizializzazione completa del progetto

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}🚀 Inizializzazione NearYou Platform${NC}"

# Crea tutte le directory necessarie
echo -e "${CYAN}Creazione struttura directory...${NC}"
mkdir -p {config/development,certs,data/osrm,logs,src/{services/{api,dashboard,message_generator},shared,core},docker/services/{app,osrm,message-generator,dashboard},infrastructure/monitoring/{grafana/provisioning,prometheus},airflow/{dags,plugins},tests/{unit,integration,e2e},docs/{api,architecture,deployment}}

# Crea file .gitkeep per mantenere le directory vuote
touch data/.gitkeep logs/.gitkeep certs/.gitkeep
touch tests/unit/.gitkeep tests/integration/.gitkeep tests/e2e/.gitkeep
touch airflow/plugins/.gitkeep
touch infrastructure/monitoring/prometheus/.gitkeep

# Imposta i permessi corretti per tutti gli script
echo -e "${CYAN}Impostazione permessi...${NC}"
find scripts -type f -name "*.sh" -exec chmod +x {} \;

# Copia la configurazione di sviluppo
if [ ! -f config/development/.env ]; then
    echo -e "${CYAN}Creazione file di configurazione...${NC}"
    if [ -f config/development/.env.development ]; then
        cp config/development/.env.development config/development/.env
        echo -e "${GREEN}✓ Configurazione copiata${NC}"
    else
        echo -e "${RED}⚠️  File .env.development non trovato${NC}"
    fi
fi

# Genera API key Groq di esempio se non presente
if grep -q "your-development-api-key-here" config/development/.env; then
    echo -e "${YELLOW}⚠️  Ricorda di aggiornare OPENAI_API_KEY nel file config/development/.env${NC}"
    echo -e "${YELLOW}   Puoi ottenere una API key gratuita su https://console.groq.com${NC}"
fi

echo -e "${GREEN}✓ Inizializzazione completata${NC}"