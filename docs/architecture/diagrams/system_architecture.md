# Diagrammi di Architettura

## Diagramma di Sistema C4 - Livello 1 (Contesto)

```plantuml
@startuml NearYou System Context
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

Person(user, "Utente Mobile", "Utente dell'applicazione NearYou")
System(nearYouSystem, "Sistema NearYou", "Fornisce notifiche e suggerimenti basati sulla posizione")
System_Ext(mapService, "Servizio Mappe", "Fornisce dati geografici e routing")
System_Ext(llmService, "Servizio LLM", "Genera testi personalizzati")

Rel(user, nearYouSystem, "Invia posizione GPS e riceve notifiche")
Rel(nearYouSystem, mapService, "Ottiene informazioni geografiche e percorsi")
Rel(nearYouSystem, llmService, "Genera messaggi personalizzati")
@enduml
@startuml NearYou Container Diagram
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

Person(user, "Utente Mobile", "Utente dell'applicazione NearYou")

System_Boundary(nearYouSystem, "Sistema NearYou") {
    Container(dashboard, "Dashboard Service", "FastAPI", "Fornisce API e UI per visualizzare posizioni e notifiche")
    Container(producer, "Position Producer", "Python", "Acquisisce dati di posizione e li pubblica su Kafka")
    Container(consumer, "Event Consumer", "Python", "Elabora eventi di posizione e genera notifiche")
    Container(messageGen, "Message Generator", "FastAPI", "Genera messaggi personalizzati usando LLM")
    
    ContainerDb(clickhouse, "ClickHouse", "Database colonnare", "Memorizza eventi utente e analitiche")
    ContainerDb(postgres, "PostgreSQL/PostGIS", "Database relazionale", "Memorizza dati geografici e di negozi")
    ContainerDb(redis, "Redis", "Cache", "Memorizza risposte LLM e dati frequenti")
    
    Container(kafka, "Kafka", "Message Broker", "Gestisce il flusso di eventi di posizione")
    Container(osrm, "OSRM", "Routing Engine", "Calcola percorsi e distanze")
    Container(monitoring, "Monitoring Stack", "Prometheus + Grafana", "Monitoraggio sistema e alerting")
}

System_Ext(llm, "Servizio LLM", "Groq")

Rel(user, dashboard, "Visualizza notifiche e posizioni", "HTTPS")
Rel(user, producer, "Invia posizione GPS", "HTTPS")

Rel(producer, kafka, "Pubblica eventi di posizione", "SSL")
Rel(consumer, kafka, "Sottoscrive a eventi di posizione", "SSL")
Rel(consumer, postgres, "Trova negozi vicini", "SQL/SSL")
Rel(consumer, messageGen, "Richiede messaggi personalizzati", "HTTPS")
Rel(consumer, clickhouse, "Salva eventi e notifiche", "SQL/SSL")

Rel(messageGen, llm, "Genera testo", "HTTPS")
Rel(messageGen, redis, "Cache risposte", "SSL")

Rel(dashboard, clickhouse, "Recupera eventi e notifiche", "SQL/SSL")
Rel(dashboard, postgres, "Recupera dati negozi", "SQL/SSL")

Rel(producer, osrm, "Calcola percorsi", "HTTP")
Rel(monitoring, dashboard, "Monitora", "HTTP")
Rel(monitoring, consumer, "Monitora", "HTTP")
Rel(monitoring, producer, "Monitora", "HTTP")
Rel(monitoring, messageGen, "Monitora", "HTTP")
@enduml

@startuml NearYou Data Flow
!theme plain
skinparam backgroundColor transparent

participant "Dispositivo\nUtente" as User
participant "Producer" as Producer
participant "Kafka" as Kafka
participant "Consumer" as Consumer
participant "PostgreSQL" as Postgres
participant "Message\nGenerator" as MessageGen
participant "ClickHouse" as ClickHouse
participant "Dashboard" as Dashboard

User -> Producer: Dati posizione GPS
Producer -> Kafka: Pubblica evento posizione
Kafka -> Consumer: Consuma evento posizione
Consumer -> Postgres: Query per negozi vicini
Postgres -> Consumer: Dati negozio + distanza
Consumer -> MessageGen: Richiesta messaggio\n(dati utente + negozio)
MessageGen -> MessageGen: Genera/recupera da cache
MessageGen -> Consumer: Messaggio personalizzato
Consumer -> ClickHouse: Salva evento con messaggio
User -> Dashboard: Richiede notifiche
Dashboard -> ClickHouse: Query per eventi/notifiche
ClickHouse -> Dashboard: Dati notifiche
Dashboard -> User: Visualizza notifiche
@enduml