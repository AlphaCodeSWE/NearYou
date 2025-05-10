# Makefile principale per NearYou Platform
# --------------------------------------

# Variabili
SHELL := /bin/bash
PYTHON := python3
PROJECT_NAME := nearyou
DOCKER_COMPOSE := docker-compose -f docker/docker-compose.dev.yml
DOCKER_COMPOSE_PROD := docker-compose -f docker/docker-compose.prod.yml
ENV_FILE := config/development/.env

# Colori per output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Target di default
.DEFAULT_GOAL := help

.PHONY: help
help: ## Mostra questo messaggio di aiuto
	@echo -e "${CYAN}NearYou Platform - Comandi disponibili:${NC}"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "${GREEN}%-20s${NC} %s\n", $$1, $$2}'

# Setup automatico completo
.PHONY: start-all
start-all: ensure-config generate-certs docker-up wait-for-services init-databases init-airflow ## Avvia l'intero ambiente (setup + servizi)
	@echo -e "${GREEN}✓ NearYou Platform avviata con successo!${NC}"
	@echo -e "${YELLOW}Dashboard: http://localhost:8003${NC}"
	@echo -e "${YELLOW}API Docs: http://localhost:8000/docs${NC}"
	@echo -e "${YELLOW}Grafana: http://localhost:3000${NC}"
	@echo -e "${YELLOW}Airflow: http://localhost:8080${NC}"

.PHONY: ensure-config
ensure-config: ## Assicura che la configurazione esista
	@if [ ! -f $(ENV_FILE) ]; then \
		echo -e "${CYAN}Creazione configurazione di sviluppo...${NC}"; \
		mkdir -p config/development; \
		cp config/development/.env.development $(ENV_FILE); \
		echo -e "${GREEN}✓ Configurazione creata${NC}"; \
	else \
		echo -e "${GREEN}✓ Configurazione esistente${NC}"; \
	fi

.PHONY: generate-certs
generate-certs: ## Genera certificati SSL per sviluppo
	@if [ ! -f certs/ca.crt ]; then \
		echo -e "${CYAN}Generazione certificati SSL...${NC}"; \
		./scripts/setup/generate_dev_certificates.sh; \
		echo -e "${GREEN}✓ Certificati generati${NC}"; \
	else \
		echo -e "${GREEN}✓ Certificati esistenti${NC}"; \
	fi

.PHONY: wait-for-services
wait-for-services: ## Attende che tutti i servizi siano pronti
	@echo -e "${CYAN}Attesa avvio servizi...${NC}"
	@./scripts/setup/wait_for_services.sh
	@echo -e "${GREEN}✓ Tutti i servizi sono pronti${NC}"

.PHONY: init-databases
init-databases: ## Inizializza i database
	@echo -e "${CYAN}Inizializzazione database...${NC}"
	@./scripts/setup/init_databases.sh
	@echo -e "${GREEN}✓ Database inizializzati${NC}"

.PHONY: init-airflow
init-airflow: ## Inizializza Airflow
	@echo -e "${CYAN}Inizializzazione Airflow...${NC}"
	@./scripts/setup/init_airflow.sh
	@echo -e "${GREEN}✓ Airflow inizializzato${NC}"

# Quick start per sviluppatori
.PHONY: dev
dev: start-all ## Alias per start-all (avvio rapido sviluppo)
	@echo -e "${GREEN}Ambiente di sviluppo pronto!${NC}"

# Docker commands
.PHONY: docker-up
docker-up: ensure-config ## Avvia tutti i servizi Docker
	@echo -e "${CYAN}Avvio servizi Docker...${NC}"
	$(DOCKER_COMPOSE) up -d
	@echo -e "${GREEN}✓ Servizi avviati${NC}"

.PHONY: docker-down
docker-down: ## Ferma tutti i servizi Docker
	@echo -e "${CYAN}Arresto servizi Docker...${NC}"
	$(DOCKER_COMPOSE) down
	@echo -e "${GREEN}✓ Servizi arrestati${NC}"

.PHONY: docker-reset
docker-reset: docker-down ## Reset completo dell'ambiente Docker
	@echo -e "${RED}⚠️  Reset completo ambiente...${NC}"
	$(DOCKER_COMPOSE) down -v
	rm -rf data/* logs/*
	@echo -e "${GREEN}✓ Reset completato${NC}"

# Development utilities
.PHONY: logs
logs: ## Mostra i log di tutti i servizi
	$(DOCKER_COMPOSE) logs -f

.PHONY: status
status: ## Mostra lo stato di tutti i servizi
	@echo -e "${CYAN}Stato servizi:${NC}"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo -e "${CYAN}Health check:${NC}"
	@./scripts/setup/check_health.sh

.PHONY: shell
shell: ## Apre una shell nel container principale
	$(DOCKER_COMPOSE) exec app bash

.PHONY: shell-db
shell-db: ## Apre una shell PostgreSQL
	$(DOCKER_COMPOSE) exec postgres psql -U nearyou -d nearyou_shops

.PHONY: shell-clickhouse
shell-clickhouse: ## Apre una shell ClickHouse
	$(DOCKER_COMPOSE) exec clickhouse clickhouse-client

# Testing
.PHONY: test
test: ## Esegue tutti i test
	@echo -e "${CYAN}Esecuzione test suite completa...${NC}"
	$(DOCKER_COMPOSE) exec app pytest tests/ -v --cov=src
	@echo -e "${GREEN}✓ Test completati${NC}"

.PHONY: test-watch
test-watch: ## Esegue test in modalità watch
	$(DOCKER_COMPOSE) exec app pytest-watch -- tests/ -v

# Code quality
.PHONY: lint
lint: ## Esegue il linting del codice
	@echo -e "${CYAN}Controllo qualità del codice...${NC}"
	$(DOCKER_COMPOSE) exec app pre-commit run --all-files
	@echo -e "${GREEN}✓ Linting completato${NC}"

.PHONY: format
format: ## Formatta il codice automaticamente
	@echo -e "${CYAN}Formattazione codice...${NC}"
	$(DOCKER_COMPOSE) exec app black src/
	$(DOCKER_COMPOSE) exec app isort src/
	@echo -e "${GREEN}✓ Codice formattato${NC}"

# Troubleshooting
.PHONY: debug
debug: ## Mostra informazioni di debug
	@echo -e "${CYAN}Informazioni di debug:${NC}"
	@echo "Environment: $(ENVIRONMENT)"
	@echo "Docker Compose file: $(DOCKER_COMPOSE)"
	@echo "Config file: $(ENV_FILE)"
	@echo ""
	@echo -e "${CYAN}Servizi in esecuzione:${NC}"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

.PHONY: fix-permissions
fix-permissions: ## Corregge i permessi dei file
	@echo -e "${CYAN}Correzione permessi...${NC}"
	@sudo chown -R $(USER):$(USER) .
	@chmod +x scripts/**/*.sh
	@echo -e "${GREEN}✓ Permessi corretti${NC}"

.PHONY: clean
clean: ## Pulisce file temporanei e cache
	@echo -e "${CYAN}Pulizia file temporanei...${NC}"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/
	@echo -e "${GREEN}✓ Pulizia completata${NC}"

# Utility per problemi comuni
.PHONY: restart-service
restart-service: ## Riavvia un servizio specifico (uso: make restart-service SERVICE=api)
	@if [ -z "$(SERVICE)" ]; then \
		echo -e "${RED}Specifica il servizio: make restart-service SERVICE=nome${NC}"; \
		exit 1; \
	fi
	@echo -e "${CYAN}Riavvio $(SERVICE)...${NC}"
	$(DOCKER_COMPOSE) restart $(SERVICE)
	@echo -e "${GREEN}✓ $(SERVICE) riavviato${NC}"