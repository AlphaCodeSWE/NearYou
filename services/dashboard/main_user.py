# services/dashboard/main_user.py

import os
import logging
import asyncio
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from clickhouse_driver import Client as CHClient

# Import nuovi moduli ristrutturati
from .api import api_router
from .api.dependencies import get_current_user, get_clickhouse_client
from .api.models import Token

# Import originali da mantenere
from .auth import authenticate_user, create_access_token

# Configura logger
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# Crea l'app FastAPI
app = FastAPI(title="NearYou User Dashboard")

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta la UI statica
static_dir = os.path.join(os.path.dirname(__file__), "frontend_user")
app.mount(
    "/static_user",
    StaticFiles(directory=static_dir),
    name="static_user",
)

# Includi il router API
app.include_router(api_router, prefix="/api")

# Login e generazione token
@app.post("/api/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint per l'autenticazione e generazione token JWT."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Credenziali errate")
    token = create_access_token({"user_id": user["user_id"]})
    return {"access_token": token, "token_type": "bearer"}

# Reindirizza dalla radice alla dashboard utente
@app.get("/", response_class=RedirectResponse)
async def root():
    """Reindirizza dalla radice del sito alla dashboard utente."""
    return RedirectResponse(url="/dashboard/user")

# Dashboard utente principale
@app.get("/dashboard/user", response_class=HTMLResponse)
async def user_dashboard():
    """Endpoint che serve la dashboard utente."""
    html_path = os.path.join(static_dir, "index_user.html")
    with open(html_path, encoding="utf8") as f:
        return HTMLResponse(f.read())

# Endpoint di debug per le env vars
@app.get("/__debug/env")
async def debug_env():
    """Endpoint di debug per verificare le variabili d'ambiente."""
    return {
        "JWT_SECRET": os.getenv("JWT_SECRET")[:5] + "..." if os.getenv("JWT_SECRET") else None,
        "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM"),
        "CLICKHOUSE_HOST": os.getenv("CLICKHOUSE_HOST"),
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
    }

# WebSocket Manager con cache posizioni
class ConnectionManager:
    def __init__(self):
        # Dizionario user_id -> connessione WebSocket
        self.active_connections = {}
        # Cache posizioni utente per evitare query continue
        self.position_cache = {}
        
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"Utente {user_id} connesso via WebSocket. Connessioni attive: {len(self.active_connections)}")
        
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.position_cache:
            del self.position_cache[user_id]
        logger.info(f"Utente {user_id} disconnesso. Connessioni attive: {len(self.active_connections)}")
    
    async def send_position_update(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Errore invio aggiornamento a utente {user_id}: {e}")
                self.disconnect(user_id)
                return False
        return False
    
    def has_position_changed(self, user_id: int, new_position: dict) -> bool:
        """Verifica se la posizione è cambiata significativamente"""
        if user_id not in self.position_cache:
            return True
            
        old_pos = self.position_cache[user_id]
        
        # Calcola distanza semplice (approssimativa)
        lat_diff = abs(new_position.get('latitude', 0) - old_pos.get('latitude', 0))
        lon_diff = abs(new_position.get('longitude', 0) - old_pos.get('longitude', 0))
        
        # Soglia di movimento minimo (circa 10 metri)
        threshold = 0.0001
        
        has_changed = lat_diff > threshold or lon_diff > threshold
        
        # Aggiorna cache se cambiata
        if has_changed:
            self.position_cache[user_id] = new_position
            
        return has_changed

# Istanzia il connection manager per i WebSocket
manager = ConnectionManager()

def get_visited_shops(ch_client: CHClient, user_id: int) -> list:
    """Recupera i negozi visitati dall'utente nelle ultime 24 ore."""
    try:
        result = ch_client.execute("""
            SELECT DISTINCT shop_id, shop_name, shop_category,
                   max(visit_start_time) as last_visit
            FROM user_visits
            WHERE user_id = %(user_id)s
              AND visit_start_time >= now() - INTERVAL 24 HOUR
            GROUP BY shop_id, shop_name, shop_category
            ORDER BY last_visit DESC
            LIMIT 20
        """, {"user_id": user_id})
        
        return [
            {
                "shop_id": row[0],
                "shop_name": row[1],
                "shop_category": row[2],
                "last_visit": row[3].isoformat() if row[3] else None
            }
            for row in result
        ]
    except Exception as e:
        logger.error(f"Errore recupero negozi visitati per user {user_id}: {e}")
        return []

# WebSocket per aggiornamenti posizione in tempo reale - OTTIMIZZATO
@app.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket):
    await websocket.accept()
    
    user_id = None
    
    try:
        # Prima ricezione: il client invia il token
        auth_data = await websocket.receive_json()
        token = auth_data.get("token")
        
        if not token:
            await websocket.send_json({"error": "Token non fornito"})
            await websocket.close(code=1008)
            return
        
        # Verifica il token JWT
        try:
            payload = jwt.decode(
                token, 
                os.getenv("JWT_SECRET"), 
                algorithms=[os.getenv("JWT_ALGORITHM")]
            )
            user_id = payload.get("user_id")
            
            if not user_id:
                await websocket.send_json({"error": "Token non valido"})
                await websocket.close(code=1008)
                return
                
        except Exception as e:
            logger.error(f"Errore verifica token WebSocket: {e}")
            await websocket.send_json({"error": "Token non valido"})
            await websocket.close(code=1008)
            return
        
        # Registra la connessione
        await manager.connect(websocket, user_id)
        
        # Invia conferma di connessione
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id
        })
        
        # Crea client ClickHouse per questo WebSocket
        ch = CHClient(
            host=os.getenv("CLICKHOUSE_HOST", "clickhouse-server"),
            port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            database=os.getenv("CLICKHOUSE_DATABASE", "nearyou"),
        )
        
        # Loop principale: invia aggiornamenti posizione - RIDOTTA FREQUENZA
        while True:
            # Recupera ultima posizione dell'utente
            position_query = """
                SELECT
                    user_id,
                    argMax(latitude, event_time) AS lat,
                    argMax(longitude, event_time) AS lon,
                    argMax(poi_info, event_time) AS msg,
                    max(event_time) as time
                FROM user_events
                WHERE user_id = %(uid)s
                GROUP BY user_id
                LIMIT 1
            """
            
            rows = ch.execute(position_query, {"uid": user_id})
            
            if rows:
                r = rows[0]
                time_str = r[4].strftime("%Y-%m-%d %H:%M:%S") if r[4] else None
                
                new_position = {
                    "user_id": r[0],
                    "latitude": r[1],
                    "longitude": r[2],
                    "message": r[3] or None,
                    "timestamp": time_str
                }
                
                # OTTIMIZZAZIONE: Invia solo se posizione cambiata
                if manager.has_position_changed(user_id, new_position):
                    # Recupera negozi visitati solo quando posizione cambia
                    visited_shops = get_visited_shops(ch, user_id)
                    new_position["visited_shops"] = visited_shops
                    
                    await websocket.send_json({
                        "type": "position_update",
                        "data": new_position
                    })
                    
                    logger.debug(f"Posizione aggiornata per user {user_id}")
            
            # RIDOTTA FREQUENZA: da 1 secondo a 3 secondi
            await asyncio.sleep(3)
            
    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Errore WebSocket: {e}")
        if user_id:
            manager.disconnect(user_id)

# Configurazione metriche Prometheus
try:
    from .metrics import setup_metrics
    setup_metrics(app, app_name="dashboard_user")
    print("Metriche Prometheus configurate con successo")
except Exception as e:
    print(f"Errore configurazione metriche: {e}")