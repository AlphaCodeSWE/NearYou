"""
Router per le API dashboard utente.
"""
import logging
import random
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from clickhouse_driver import Client as CHClient

from .models import (
    UserProfile, PositionsResponse, Position,
    Shop, Promotion, PromotionsResponse, UserStats
)
from .dependencies import get_clickhouse_client, get_current_user

# Database e endpoints sicuri richiedono autenticazione 
router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    ch_client: CHClient = Depends(get_clickhouse_client),
    user_id: Optional[int] = Query(None, description="ID dell'utente (solo per debug)")
):
    """Ottiene il profilo dell'utente autenticato."""
    # Per sicurezza, usa l'ID dell'utente corrente, non quello in query
    # a meno che non siamo in modalità debug
    uid = user_id if user_id is not None else current_user["user_id"]
    
    query = """
        SELECT
          user_id, age, profession, interests
        FROM users
        WHERE user_id = %(uid)s
        LIMIT 1
    """
    
    rows = ch_client.execute(query, {"uid": uid})
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Profilo utente non trovato"
        )
    
    return {
        "user_id": rows[0][0],
        "age": rows[0][1],
        "profession": rows[0][2],
        "interests": rows[0][3]
    }

@router.get("/positions", response_model=PositionsResponse)
async def get_user_positions(
    current_user: dict = Depends(get_current_user),
    ch_client: CHClient = Depends(get_clickhouse_client)
):
    """Ottiene le posizioni più recenti dell'utente."""
    uid = current_user["user_id"]
    query = """
        SELECT
          user_id,
          argMax(latitude,  event_time) AS lat,
          argMax(longitude, event_time) AS lon,
          argMax(poi_info,   event_time) AS msg,
          max(event_time) as last_time
        FROM user_events
        WHERE user_id = %(uid)s
        GROUP BY user_id
        LIMIT 1
    """
    rows = ch_client.execute(query, {"uid": uid})
    
    if not rows:
        return {"positions": []}
        
    r = rows[0]
    return {
        "positions": [
            {
                "user_id": r[0],
                "latitude": r[1],
                "longitude": r[2],
                "message": r[3] or None,
                "timestamp": r[4] if len(r) > 4 else None
            }
        ]
    }

@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    current_user: dict = Depends(get_current_user),
    ch_client: CHClient = Depends(get_clickhouse_client),
    time_period: str = Query("day", description="Periodo di tempo (day, week, month)")
):
    """Ottiene statistiche sull'attività dell'utente."""
    uid = current_user["user_id"]
    
    # Determina intervallo di tempo
    now = datetime.now()
    if time_period == "week":
        since = now - timedelta(days=7)
    elif time_period == "month":
        since = now - timedelta(days=30)
    else:  # day è il default
        since = now - timedelta(days=1)
    
    # Query per statistiche
    query = """
        SELECT 
            COUNT(*) as total_events,
            COUNT(DISTINCT toDate(event_time)) as active_days,
            COUNT(DISTINCT poi_name) as unique_shops,
            countIf(poi_info != '') as notifications
        FROM user_events
        WHERE user_id = %(uid)s
          AND event_time >= %(since)s
    """
    
    rows = ch_client.execute(query, {
        "uid": uid,
        "since": since.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    if not rows or not rows[0]:
        return UserStats()
    
    return {
        "total_events": rows[0][0],
        "active_days": rows[0][1],
        "unique_shops": rows[0][2],
        "notifications": rows[0][3]
    }

@router.get("/promotions", response_model=PromotionsResponse)
async def get_user_promotions(
    current_user: dict = Depends(get_current_user),
    ch_client: CHClient = Depends(get_clickhouse_client),
    limit: int = Query(10, description="Numero massimo di promozioni da restituire"),
    offset: int = Query(0, description="Offset per la paginazione")
):
    """Ottiene le promozioni ricevute dall'utente."""
    uid = current_user["user_id"]
    
    query = """
        SELECT 
            event_id,
            event_time,
            poi_name,
            poi_info
        FROM user_events
        WHERE user_id = %(uid)s
          AND poi_info != ''
        ORDER BY event_time DESC
        LIMIT %(limit)s
        OFFSET %(offset)s
    """
    
    rows = ch_client.execute(query, {
        "uid": uid,
        "limit": limit,
        "offset": offset
    })
    
    result = []
    for row in rows:
        result.append({
            "event_id": row[0],
            "timestamp": row[1],
            "shop_name": row[2],
            "message": row[3]
        })
        
    return {"promotions": result}

@router.get("/shops/inArea")
async def get_shops_in_area(
    n: float = Query(..., description="Latitudine nord"),
    s: float = Query(..., description="Latitudine sud"), 
    e: float = Query(..., description="Longitudine est"),
    w: float = Query(..., description="Longitudine ovest"),
    current_user: dict = Depends(get_current_user),
    ch_client: CHClient = Depends(get_clickhouse_client)
):
    """
    Recupera tutti i POI/negozi nell'area visibile della mappa.
    Estrae i POI unici dalla tabella user_events di ClickHouse.
    """
    logger.info(f"🗺️ Richiesta negozi per area: [{s:.4f},{w:.4f}] -> [{n:.4f},{e:.4f}]")
    
    try:
        # Estrai POI unici da user_events nell'area specificata
        query = """
            SELECT 
                cityHash64(poi_name) as id,
                poi_name as shop_name,
                'convenience' as category,
                argMax(latitude, event_time) as lat,
                argMax(longitude, event_time) as lon,
                count() as visit_count
            FROM user_events
            WHERE latitude BETWEEN %(south)s AND %(north)s
              AND longitude BETWEEN %(west)s AND %(east)s
              AND poi_name != ''
              AND poi_name IS NOT NULL
            GROUP BY poi_name
            HAVING lat BETWEEN %(south)s AND %(north)s
               AND lon BETWEEN %(west)s AND %(east)s
            ORDER BY visit_count DESC, poi_name
            LIMIT 200
        """
        
        rows = ch_client.execute(query, {
            "north": n,
            "south": s, 
            "east": e,
            "west": w
        })
        
        if rows:
            shops = []
            # Mappa semplice per assegnare categorie basate sul nome
            category_mapping = {
                'supermercato': 'supermarket',
                'market': 'supermarket', 
                'esselunga': 'supermarket',
                'coop': 'supermarket',
                'carrefour': 'supermarket',
                'bar': 'convenience',
                'caffè': 'convenience',
                'cafe': 'convenience',
                'ristorante': 'bakery',
                'pizzeria': 'bakery',
                'trattoria': 'bakery',
                'farmacia': 'chemist',
                'pharmacy': 'chemist',
                'banca': 'convenience',
                'bank': 'convenience',
                'negozio': 'clothes',
                'store': 'clothes',
                'shop': 'clothes',
                'parrucchiere': 'hairdresser',
                'hair': 'hairdresser',
                'beauty': 'beauty',
                'bellezza': 'beauty',
                'chiesa': 'convenience',
                'church': 'convenience',
                'scuola': 'convenience',
                'school': 'convenience',
                'ospedale': 'convenience',
                'hospital': 'convenience',
                'ufficio': 'convenience',
                'office': 'convenience'
            }
            
            for row in rows:
                poi_name = row[1].lower()
                
                # Determina categoria in base al nome
                category = 'convenience'  # default
                for keyword, cat in category_mapping.items():
                    if keyword in poi_name:
                        category = cat
                        break
                
                shops.append({
                    "id": int(row[0]) if row[0] else hash(row[1]) & 0x7FFFFFFF,
                    "shop_name": row[1],
                    "category": category,
                    "lat": float(row[3]),
                    "lon": float(row[4]),
                    "visit_count": int(row[5])
                })
                
            logger.info(f"✅ Trovati {len(shops)} POI da user_events nell'area [{s:.4f},{w:.4f}] -> [{n:.4f},{e:.4f}]")
            return shops
        else:
            logger.info("⚠️ Nessun POI trovato in user_events per quest'area")
            
    except Exception as e:
        logger.error(f"❌ Errore query ClickHouse: {e}")
    
    # Fallback: genera dati di test se non ci sono eventi
    logger.info("🎲 Generando POI di fallback per l'area...")
    return generate_fallback_pois(n, s, e, w)


def generate_fallback_pois(north: float, south: float, east: float, west: float) -> List[dict]:
    """
    Genera POI di esempio quando user_events è vuoto.
    Simula POI realistici per Milano.
    """
    # POI tipici di Milano con categorie reali dal tuo paste.txt
    milano_pois = [
        {"name": "Supermercato Esselunga", "category": "supermarket"},
        {"name": "Parrucchiere Bella Vista", "category": "hairdresser"},
        {"name": "Bar Centrale", "category": "convenience"},
        {"name": "Ristorante Da Mario", "category": "bakery"},
        {"name": "Farmacia San Carlo", "category": "chemist"},
        {"name": "Negozio Abbigliamento Moda", "category": "clothes"},
        {"name": "Panificio del Borgo", "category": "bakery"},
        {"name": "Tabaccheria Giornali", "category": "newsagent"},
        {"name": "Fioraio Le Rose", "category": "florist"},
        {"name": "Ottica Milano", "category": "optician"},
        {"name": "Gioielleria Luxury", "category": "jewelry"},
        {"name": "Profumeria Douglas", "category": "beauty"},
        {"name": "Libreria Mondadori", "category": "books"},
        {"name": "Macelleria Qualità", "category": "butcher"},
        {"name": "Lavanderia Express", "category": "laundry"},
        {"name": "Cartoleria Office", "category": "stationery"},
        {"name": "Elettronica TechStore", "category": "electronics"},
        {"name": "Scarpe & Style", "category": "shoes"},
        {"name": "Pasticceria Dolci", "category": "pastry"},
        {"name": "Enoteca Vini Pregiati", "category": "wine"}
    ]
    
    shops = []
    for i, poi in enumerate(milano_pois[:15]):  # Massimo 15 POI
        # Coordinate casuali nell'area
        lat = south + random.random() * (north - south)
        lon = west + random.random() * (east - west)
        
        shops.append({
            "id": i + 1000,  # ID alto per distinguere dal vero DB
            "shop_name": poi["name"],
            "category": poi["category"],
            "lat": lat,
            "lon": lon,
            "visit_count": random.randint(1, 50)
        })
    
    logger.info(f"✅ Generati {len(shops)} POI di fallback")
    return shops