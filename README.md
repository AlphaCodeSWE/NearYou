# NearYou: Sistema di Notifiche basate sulla Posizione

## Panoramica
NearYou è una piattaforma che offre notifiche personalizzate agli utenti quando si trovano in prossimità di negozi o punti di interesse. Utilizzando tecnologie di streaming dati, database geospaziali e generazione di messaggi con LLM, il sistema crea un'esperienza utente contestuale e personalizzata.

## Caratteristiche Principali
- Tracciamento posizioni in tempo reale con Kafka
- Ricerca geospaziale di negozi vicini con PostgreSQL/PostGIS
- Messaggi personalizzati generati con LLM (via Groq/OpenAI)
- Dashboard utente interattiva con visualizzazione mappa
- Monitoraggio e analisi completi con Grafana e Prometheus

## Architettura
![Architettura del Sistema](docs/architecture/diagrams/architecture_overview.png)

NearYou utilizza un'architettura a microservizi:
- **Data Pipeline**: Producer e Consumer Kafka per elaborazione eventi posizione
- **Message Generator**: Servizio di generazione messaggi personalizzati
- **Dashboard**: Interfaccia web per visualizzare notifiche e posizioni
- **Storage**: ClickHouse per analytics, PostgreSQL/PostGIS per dati geospaziali
- **Cache**: Redis per memorizzare risposte LLM e migliorare performance

## Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 16+ (for frontend development)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/AlphaCodeSWE/NearYou.git
   cd NearYou
   ```

2. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   make up
   # or
   docker-compose up -d
   ```

4. **Access the application**
   - Dashboard: http://localhost:8080
   - Grafana: http://localhost:3000
   - API: http://localhost:8000

[Documentazione architetturale dettagliata](docs/architecture/overview.md)

## Usage

### Basic Operations

**Start the system:**
```bash
docker-compose up -d
```

**Monitor services:**
```bash
docker-compose ps
docker-compose logs -f
```

**Stop the system:**
```bash
docker-compose down
```

### API Usage

Access the REST APIs:
- User Dashboard: `http://localhost:8003`
- Message Generator: `http://localhost:8001/health`
- Monitoring: `http://localhost:3000`

Example API call:
```bash
curl http://localhost:8001/health
```

## Installazione e Setup

### Prerequisiti
- Docker e Docker Compose
- Git
- Make (opzionale)

### Installazione Rapida
```bash
# Clona il repository
git clone https://github.com/yourusername/nearyou.git
cd nearyou

# Configura le variabili d'ambiente
cp .env.example .env
# Modifica .env con i tuoi valori

# Avvia i servizi
docker-compose up -d