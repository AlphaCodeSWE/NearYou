"""Operatori custom per Bytewax dataflow con Observer Pattern e Singleton."""
import asyncio
import logging
import random
from typing import Dict, Any, Optional, Tuple, List, Protocol
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

import asyncpg
import httpx
from clickhouse_driver import Client as CHClient

from src.configg import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE,
    MESSAGE_GENERATOR_URL,
)

logger = logging.getLogger(__name__)

# Soglia distanza per messaggi
MAX_POI_DISTANCE = 200  # metri

# Configurazione simulazione visite
VISIT_PROBABILITY_BASE = 0.3  # 30% probabilità base
VISIT_DURATION_RANGES = {
    'ristorante': (15, 45),     # 15-45 minuti
    'bar': (5, 20),             # 5-20 minuti
    'supermercato': (10, 30),   # 10-30 minuti
    'abbigliamento': (15, 40),  # 15-40 minuti
    'elettronica': (20, 60),    # 20-60 minuti
    'farmacia': (3, 10),        # 3-10 minuti
    'libreria': (10, 30),       # 10-30 minuti
    'gelateria': (5, 15),       # 5-15 minuti
    'parrucchiere': (30, 90),   # 30-90 minuti
    'palestra': (45, 120),      # 45-120 minuti
}

# Observer Pattern Implementation
class Observer(ABC):
    """Abstract observer for monitoring events."""
    
    @abstractmethod
    def update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Update observer with new event."""
        pass

class Subject(ABC):
    """Abstract subject that observers can subscribe to."""
    
    def __init__(self):
        self._observers: List[Observer] = []
    
    def attach(self, observer: Observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"Attached observer: {type(observer).__name__}")
    
    def detach(self, observer: Observer) -> None:
        """Detach an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
            logger.debug(f"Detached observer: {type(observer).__name__}")
    
    def notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """Notify all observers."""
        for observer in self._observers:
            try:
                observer.update(event_type, data)
            except Exception as e:
                logger.error(f"Error notifying observer {type(observer).__name__}: {e}")

class MetricsObserver(Observer):
    """Observer for collecting metrics."""
    
    def __init__(self):
        self.metrics = {
            "events_processed": 0,
            "messages_generated": 0,
            "visits_simulated": 0,
            "errors": 0,
            "shops_found": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Update metrics based on event."""
        if event_type == "event_processed":
            self.metrics["events_processed"] += 1
        elif event_type == "message_generated":
            self.metrics["messages_generated"] += 1
        elif event_type == "visit_simulated":
            self.metrics["visits_simulated"] += 1
        elif event_type == "error":
            self.metrics["errors"] += 1
        elif event_type == "shop_found":
            self.metrics["shops_found"] += 1
        elif event_type == "cache_hit":
            self.metrics["cache_hits"] += 1
        elif event_type == "cache_miss":
            self.metrics["cache_misses"] += 1
        
        # Log every 100 events
        if self.metrics["events_processed"] % 100 == 0:
            logger.info(f"Metrics: {self.metrics}")
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics."""
        return self.metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        for key in self.metrics:
            self.metrics[key] = 0

class PerformanceObserver(Observer):
    """Observer for performance monitoring."""
    
    def __init__(self):
        self.processing_times: List[float] = []
        self.start_times: Dict[str, float] = {}
    
    def update(self, event_type: str, data: Dict[str, Any]) -> None:
        """Update performance metrics."""
        if event_type == "processing_start":
            event_id = data.get("event_id", "unknown")
            self.start_times[event_id] = datetime.now().timestamp()
        elif event_type == "processing_end":
            event_id = data.get("event_id", "unknown")
            if event_id in self.start_times:
                duration = datetime.now().timestamp() - self.start_times[event_id]
                self.processing_times.append(duration)
                del self.start_times[event_id]
                
                # Keep only last 1000 measurements
                if len(self.processing_times) > 1000:
                    self.processing_times = self.processing_times[-1000:]
    
    def get_avg_processing_time(self) -> float:
        """Get average processing time."""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def get_latest_processing_times(self, count: int = 10) -> List[float]:
        """Get latest processing times."""
        return self.processing_times[-count:]

class DatabaseConnections(Subject):
    """Gestisce connessioni database con pattern singleton, pooling e Observer."""
    
    _instance: Optional['DatabaseConnections'] = None
    
    def __new__(cls) -> 'DatabaseConnections':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        super().__init__()  # Initialize Subject
        
        self._pg_pool = None
        self._ch_client = None
        self._http_client = None
        self._loop = None
        self._message_cache = {}  # Cache semplice in-memory
        self._initialized = True
        
        # Initialize observers
        self._metrics_observer = MetricsObserver()
        self._performance_observer = PerformanceObserver()
        self.attach(self._metrics_observer)
        self.attach(self._performance_observer)
        
        logger.info("DatabaseConnections singleton initialized with observers")
    
    @property
    def loop(self):
        """Get or create event loop."""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop
        
    async def get_pg_pool(self) -> asyncpg.Pool:
        """Ottieni pool PostgreSQL (lazy init)."""
        if self._pg_pool is None:
            self._pg_pool = await asyncpg.create_pool(
                host=POSTGRES_HOST, port=POSTGRES_PORT,
                user=POSTGRES_USER, password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                min_size=2, max_size=10,
                command_timeout=10
            )
            logger.info("PostgreSQL pool initialized")
        return self._pg_pool
        
    def get_ch_client(self) -> CHClient:
        """Ottieni client ClickHouse (lazy init)."""
        if self._ch_client is None:
            self._ch_client = CHClient(
                host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT,
                user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD,
                database=CLICKHOUSE_DATABASE,
                send_receive_timeout=10
            )
            logger.info("ClickHouse client initialized")
        return self._ch_client
        
    async def get_http_client(self) -> httpx.AsyncClient:
        """Ottieni client HTTP (lazy init)."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
            logger.info("HTTP client initialized")
        return self._http_client
        
    def get_cache_key(self, user_id: int, shop_id: int) -> str:
        """Genera chiave cache per messaggi."""
        return f"{user_id}:{shop_id}"
    
    def get_cached_message(self, user_id: int, shop_id: int) -> Optional[str]:
        """Get cached message and notify observers."""
        cache_key = self.get_cache_key(user_id, shop_id)
        if cache_key in self._message_cache:
            self.notify("cache_hit", {"user_id": user_id, "shop_id": shop_id})
            return self._message_cache[cache_key]
        else:
            self.notify("cache_miss", {"user_id": user_id, "shop_id": shop_id})
            return None
    
    def cache_message(self, user_id: int, shop_id: int, message: str) -> None:
        """Cache message."""
        cache_key = self.get_cache_key(user_id, shop_id)
        self._message_cache[cache_key] = message
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics from observers."""
        return {
            "metrics": self._metrics_observer.get_metrics(),
            "avg_processing_time": self._performance_observer.get_avg_processing_time(),
            "latest_processing_times": self._performance_observer.get_latest_processing_times()
        }
        
    async def close(self):
        """Chiudi tutte le connessioni."""
        if self._pg_pool:
            await self._pg_pool.close()
            logger.info("PostgreSQL pool closed")
        if self._http_client:
            await self._http_client.aclose()
            logger.info("HTTP client closed")

# Get singleton instance
def get_db_connections() -> DatabaseConnections:
    """Get the singleton DatabaseConnections instance."""
    return DatabaseConnections()

# Funzioni helper asincrone
async def _find_nearest_shop(conn: DatabaseConnections, lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Trova il negozio più vicino usando PostGIS."""
    try:
        pool = await conn.get_pg_pool()
        row = await pool.fetchrow(
            """
            SELECT
              shop_id,
              shop_name,
              category,
              ST_Distance(
                geom::geography,
                ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
              ) AS distance
            FROM shops
            ORDER BY distance
            LIMIT 1
            """,
            lon, lat
        )
        
        if row:
            shop_data = {
                "shop_id": row["shop_id"],
                "shop_name": row["shop_name"],
                "category": row["category"],
                "distance": row["distance"]
            }
            conn.notify("shop_found", shop_data)
            return shop_data
        return None
    except Exception as e:
        logger.error(f"Errore query PostGIS: {e}")
        conn.notify("error", {"error": str(e), "function": "_find_nearest_shop"})
        return None

async def _get_user_profile(conn: DatabaseConnections, user_id: int) -> Optional[Dict[str, Any]]:
    """Recupera profilo utente da ClickHouse."""
    try:
        ch = conn.get_ch_client()
        result = ch.execute(
            """
            SELECT user_id, age, profession, interests
            FROM users
            WHERE user_id = %(user_id)s
            LIMIT 1
            """,
            {"user_id": user_id}
        )
        if result:
            return {
                "user_id": result[0][0],
                "age": result[0][1],
                "profession": result[0][2],
                "interests": result[0][3]
            }
        return None
    except Exception as e:
        logger.error(f"Errore recupero profilo utente {user_id}: {e}")
        conn.notify("error", {"error": str(e), "function": "_get_user_profile", "user_id": user_id})
        return None

async def _generate_message(conn: DatabaseConnections, user: Dict, shop: Dict) -> str:
    """Genera messaggio personalizzato via API."""
    try:
        # Check cache first
        cached_message = conn.get_cached_message(user["user_id"], shop["shop_id"])
        if cached_message:
            logger.debug(f"Cache hit per user {user['user_id']}, shop {shop['shop_id']}")
            return cached_message
            
        # Call API
        client = await conn.get_http_client()
        payload = {
            "user": {
                "age": user["age"],
                "profession": user["profession"],
                "interests": user["interests"]
            },
            "poi": {
                "name": shop["shop_name"],
                "category": shop["category"],
                "description": f"Negozio a {shop['distance']:.0f}m di distanza",
                "shop_id": shop["shop_id"]  # Aggiunto per recuperare offerte
            }
        }
        
        response = await client.post(MESSAGE_GENERATOR_URL, json=payload)
        if response.status_code == 200:
            message = response.json()["message"]
            
            #  Fix per placeholder non sostituiti
            message = message.replace("[Nome del Negozio", shop["shop_name"])
            message = message.replace("Nome del Negozio", shop["shop_name"])
            message = message.replace("{shop_name}", shop["shop_name"])
            message = message.replace("{name}", shop["shop_name"])
            
            # Rimuovi eventuali bracket rimasti
            import re
            message = re.sub(r'\[.*?\]', shop["shop_name"], message)
            
            # Cache result
            conn.cache_message(user["user_id"], shop["shop_id"], message)
            conn.notify("message_generated", {"user_id": user["user_id"], "shop_id": shop["shop_id"]})
            return message
        else:
            logger.error(f"Errore API: {response.status_code}")
            conn.notify("error", {"error": f"API error: {response.status_code}", "function": "_generate_message"})
            return ""
    except Exception as e:
        logger.error(f"Errore generazione messaggio: {e}")
        conn.notify("error", {"error": str(e), "function": "_generate_message"})
        return ""

def _should_simulate_visit(user: Dict, shop: Dict, message: str) -> bool:
    """Decide se simulare una visita al negozio."""
    if not message or not message.strip():
        return False
    
    # Probabilità base
    probability = VISIT_PROBABILITY_BASE
    
    # Aumenta probabilità se c'è sconto nel messaggio
    if "%" in message or "sconto" in message.lower() or "offerta" in message.lower():
        probability += 0.3
        
        # Estrai percentuale sconto se presente
        import re
        discount_match = re.search(r'(\d+)%', message)
        if discount_match:
            discount = int(discount_match.group(1))
            # Più sconto = più probabilità
            probability += min(discount / 100, 0.4)  # Max +40%
    
    # Modifica per categoria
    category = shop.get("category", "").lower()
    category_multipliers = {
        'ristorante': 1.2,
        'bar': 1.3,
        'gelateria': 1.4,
        'abbigliamento': 1.1,
        'supermercato': 0.9,
        'farmacia': 0.7,
    }
    probability *= category_multipliers.get(category, 1.0)
    
    # Modifica per età utente
    age = user.get("age", 30)
    if category in ['bar', 'gelateria'] and age < 35:
        probability *= 1.2
    elif category in ['farmacia'] and age > 50:
        probability *= 1.3
    
    # Cap la probabilità al 90%
    probability = min(probability, 0.9)
    
    decision = random.random() < probability
    logger.debug(f"Decisione visita per user {user['user_id']} al negozio {shop['shop_name']}: "
                f"probabilità={probability:.2f}, decisione={decision}")
    
    return decision

def _create_simulated_visit(conn: DatabaseConnections, user: Dict, shop: Dict) -> None:
    """Crea un record di visita simulata nel database."""
    try:
        # Calcola durata della visita
        category = shop.get("category", "").lower()
        duration_range = VISIT_DURATION_RANGES.get(category, (10, 30))
        duration_minutes = random.randint(duration_range[0], duration_range[1])
        
        # Genera dati della visita
        visit_start = datetime.now(timezone.utc).replace(tzinfo=None)
        visit_end = visit_start.replace(minute=visit_start.minute + duration_minutes)
        
        # Probabilità di accettare l'offerta (se presente)
        offer_accepted = random.random() < 0.7  # 70% accetta offerta
        
        # Spesa stimata basata su categoria
        spending_ranges = {
            'ristorante': (15, 80),
            'bar': (3, 15),
            'supermercato': (20, 120),
            'abbigliamento': (25, 200),
            'elettronica': (50, 500),
            'farmacia': (8, 40),
            'libreria': (10, 50),
            'gelateria': (3, 12),
            'parrucchiere': (25, 80),
            'palestra': (30, 100),
        }
        spending_range = spending_ranges.get(category, (10, 50))
        estimated_spending = random.uniform(spending_range[0], spending_range[1])
        
        # Soddisfazione (1-10)
        satisfaction = random.randint(6, 10)  # Generalmente positiva
        
        # Inserisci nel database
        ch = conn.get_ch_client()
        
        # Genera ID visita unico
        visit_id = random.randint(100000, 999999)
        
        visit_data = (
            visit_id,
            user["user_id"],
            shop["shop_id"],
            0,  # offer_id (da implementare se necessario)
            visit_start,
            visit_end,
            duration_minutes,
            offer_accepted,
            estimated_spending,
            satisfaction,
            visit_start.weekday() + 1,  # day_of_week
            visit_start.hour,          # hour_of_day
            "",                        # weather_condition
            user.get("age", 0),
            user.get("profession", ""),
            user.get("interests", ""),
            shop.get("shop_name", ""),
            shop.get("category", ""),
            datetime.now(timezone.utc).replace(tzinfo=None)  # created_at
        )
        
        ch.execute("""
            INSERT INTO user_visits (
                visit_id, user_id, shop_id, offer_id, visit_start_time, visit_end_time,
                duration_minutes, offer_accepted, estimated_spending, user_satisfaction,
                day_of_week, hour_of_day, weather_condition, user_age, user_profession,
                user_interests, shop_name, shop_category, created_at
            ) VALUES
        """, [visit_data])
        
        conn.notify("visit_simulated", {
            "user_id": user["user_id"],
            "shop_id": shop["shop_id"],
            "duration_minutes": duration_minutes,
            "estimated_spending": estimated_spending
        })
        
        logger.info(f"📍 Visita simulata: User {user['user_id']} → {shop['shop_name']} "
                   f"({duration_minutes}min, €{estimated_spending:.1f})")
        
    except Exception as e:
        logger.error(f"Errore creazione visita simulata: {e}")
        conn.notify("error", {"error": str(e), "function": "_create_simulated_visit"})

# Operatori Bytewax
def enrich_with_nearest_shop(item: Tuple[str, Dict]) -> List[Tuple[str, Dict]]:
    """Arricchisce evento con negozio più vicino."""
    key, event = item
    conn = get_db_connections()
    
    # Notify processing start
    conn.notify("processing_start", {"event_id": key})
    
    # Esegui query asincrona in modo sincrono
    loop = conn.loop
    shop = loop.run_until_complete(
        _find_nearest_shop(conn, event["latitude"], event["longitude"])
    )
    
    if shop:
        # Merge shop data into event
        event.update(shop)
        result = [(key, event)]
    else:
        logger.warning(f"Nessun negozio trovato per user {key}")
        result = []
    
    # Notify processing end
    conn.notify("processing_end", {"event_id": key})
    conn.notify("event_processed", {"user_id": key})
    
    return result

def check_proximity_and_generate_message(item: Tuple[str, Dict]) -> List[Tuple[str, Dict]]:
    """Genera messaggio se utente è in prossimità."""
    key, event = item
    conn = get_db_connections()
    
    # Notify processing start
    conn.notify("processing_start", {"event_id": f"{key}_message"})
    
    # Check distanza
    distance = event.get("distance", float('inf'))
    if distance > MAX_POI_DISTANCE:
        # Troppo lontano, passa evento senza messaggio
        event["poi_info"] = ""
        conn.notify("processing_end", {"event_id": f"{key}_message"})
        return [(key, event)]
    
    # Recupera profilo e genera messaggio
    loop = conn.loop
    user_profile = loop.run_until_complete(
        _get_user_profile(conn, int(key))
    )
    
    if user_profile:
        message = loop.run_until_complete(
            _generate_message(conn, user_profile, event)
        )
        event["poi_info"] = message
        
        # NUOVA FUNZIONALITÀ: Simula visita se condizioni sono favorevoli
        if message and message.strip():
            should_visit = _should_simulate_visit(user_profile, event, message)
            if should_visit:
                _create_simulated_visit(conn, user_profile, event)
                event["visited_shop"] = True
                event["visited_shop_id"] = event.get("shop_id")
            else:
                event["visited_shop"] = False
        else:
            event["visited_shop"] = False
    else:
        event["poi_info"] = ""
        event["visited_shop"] = False
    
    # Notify processing end
    conn.notify("processing_end", {"event_id": f"{key}_message"})
    return [(key, event)]

def write_to_clickhouse(item: Tuple[str, Dict]) -> None:
    """Scrive evento in ClickHouse."""
    key, event = item
    conn = get_db_connections()
    
    # Notify processing start
    conn.notify("processing_start", {"event_id": f"{key}_write"})
    
    try:
        ch = conn.get_ch_client()
        
        # Parse timestamp
        ts = datetime.fromisoformat(event["timestamp"]).astimezone(timezone.utc).replace(tzinfo=None)
        
        # Insert
        ch.execute(
            """
            INSERT INTO user_events
              (event_id, event_time, user_id, latitude, longitude, 
               poi_range, poi_name, poi_info)
            VALUES
            """,
            [(
                event.get("_offset", 0),
                ts,
                int(key),
                event["latitude"],
                event["longitude"],
                event.get("distance", 0),
                event.get("shop_name", ""),
                event.get("poi_info", "")
            )]
        )
        
        if event.get("poi_info"):
            logger.info(f"💬 Evento con messaggio salvato per user {key}")
        if event.get("visited_shop"):
            logger.info(f"🏪 Visita simulata registrata per user {key}")
            
    except Exception as e:
        logger.error(f"Errore scrittura ClickHouse: {e}")
        conn.notify("error", {"error": str(e), "function": "write_to_clickhouse"})
    
    # Notify processing end
    conn.notify("processing_end", {"event_id": f"{key}_write"})