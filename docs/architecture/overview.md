# Panoramica dell'Architettura NearYou

## Introduzione

NearYou è una piattaforma location-based che offre agli utenti notifiche personalizzate basate sulla prossimità ai negozi. Il sistema utilizza una architettura event-driven e microservizi per elaborare dati di posizione in tempo reale e generare messaggi personalizzati.

## Componenti Principali

### 1. Data Pipeline
- **Producer**: Acquisisce dati di posizione GPS e li pubblica sul topic Kafka
- **Consumer**: Elabora gli eventi di posizione, trova negozi nelle vicinanze e genera notifiche

### 2. Servizi
- **Message Generator**: Genera messaggi personalizzati per gli utenti utilizzando LLM
- **Dashboard Service**: Fornisce API e interfaccia utente per visualizzare posizioni e notifiche

### 3. Storage
- **ClickHouse**: Database colonnare per l'analisi di eventi utente ad alto volume
- **PostgreSQL/PostGIS**: Database relazionale con estensioni spaziali per dati geografici
- **Redis**: Caching per le risposte LLM e altri dati frequentemente acceduti

### 4. Infrastruttura
- **Kafka**: Message broker per la gestione del flusso di eventi
- **OSRM**: Open Source Routing Machine per il calcolo di percorsi
- **Docker/Kubernetes**: Containerizzazione e orchestrazione
- **Monitoring Stack**: Prometheus, Grafana, Loki per monitoraggio e logging

## Flusso dei Dati

1. Un dispositivo utente invia dati di posizione GPS
2. Il Producer pubblica questi dati su un topic Kafka
3. Il Consumer elabora gli eventi e determina se l'utente è vicino a un negozio
4. Se l'utente è in prossimità di un negozio, vengono recuperate le informazioni utente e del negozio
5. Il Message Generator crea un messaggio personalizzato basato sul profilo utente e sulla categoria del negozio
6. Il messaggio viene salvato in ClickHouse e reso disponibile all'utente tramite la Dashboard

## Sicurezza e Privacy

- Comunicazione sicura con SSL/TLS tra tutti i componenti
- Autenticazione JWT per le API
- Crittografia dei dati sensibili
- Politiche di retention per i dati di posizione

## Scalabilità

L'architettura è progettata per scalare orizzontalmente:
- I servizi sono stateless e possono essere replicati
- Kafka gestisce la distribuzione del carico tra i consumer
- ClickHouse supporta lo sharding per gestire grandi volumi di dati
- Le cache Redis migliorano le prestazioni e riducono il carico sui servizi LLM