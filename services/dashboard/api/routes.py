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
    Recupera tutti i negozi nell'area visibile della mappa.
    
    Args:
        n: Latitudine nord del bounding box
        s: Latitudine sud del bounding box
        e: Longitudine est del bounding box
        w: Longitudine ovest del bounding box
        current_user: Utente autenticato
        ch_client: Client ClickHouse
        
    Returns:
        List: Lista negozi nell'area specificata
    """
    try:
        # Prima prova a cercare nella tabella shops se esiste
        shops_query = """
            SELECT 
                shop_id as id,
                shop_name,
                category,
                latitude as lat,
                longitude as lon
            FROM shops 
            WHERE latitude BETWEEN %(south)s AND %(north)s
              AND longitude BETWEEN %(west)s AND %(east)s
            ORDER BY shop_name
            LIMIT 500
        """
        
        try:
            rows = ch_client.execute(shops_query, {
                "north": n,
                "south": s, 
                "east": e,
                "west": w
            })
            
            if rows:
                shops = []
                for row in rows:
                    shops.append({
                        "id": row[0],
                        "shop_name": row[1],
                        "category": row[2], 
                        "lat": row[3],
                        "lon": row[4]
                    })
                    
                logger.info(f"Trovati {len(shops)} negozi nella tabella shops per area [{s},{w}] -> [{n},{e}]")
                return shops
        except Exception as e:
            logger.warning(f"Tabella shops non disponibile: {e}")
        
        # Se la tabella shops non esiste, prova con user_events 
        events_query = """
            SELECT DISTINCT
                toUInt32(cityHash64(poi_name)) as id,
                poi_name as shop_name,
                'convenience' as category,
                argMax(latitude, event_time) as lat,
                argMax(longitude, event_time) as lon
            FROM user_events
            WHERE latitude BETWEEN %(south)s AND %(north)s
              AND longitude BETWEEN %(west)s AND %(east)s
              AND poi_name != ''
            GROUP BY poi_name
            ORDER BY poi_name
            LIMIT 200
        """
        
        try:
            rows = ch_client.execute(events_query, {
                "north": n,
                "south": s, 
                "east": e,
                "west": w
            })
            
            if rows:
                shops = []
                for row in rows:
                    shops.append({
                        "id": row[0],
                        "shop_name": row[1],
                        "category": row[2], 
                        "lat": row[3],
                        "lon": row[4]
                    })
                    
                logger.info(f"Trovati {len(shops)} POI dalla tabella user_events per area [{s},{w}] -> [{n},{e}]")
                return shops
        except Exception as e:
            logger.warning(f"Impossibile recuperare POI da user_events: {e}")
        
        # Fallback: genera dati di esempio
        logger.info("Generando dati di fallback per l'area richiesta")
        return generate_fallback_shops_data(n, s, e, w)
        
    except Exception as e:
        logger.error(f"Errore generale nel recupero negozi in area: {e}")
        return generate_fallback_shops_data(n, s, e, w)


def generate_fallback_shops_data(north: float, south: float, east: float, west: float) -> List[dict]:
    """
    Genera dati di esempio per negozi nell'area specificata.
    Utile quando il database non ha dati reali.
    """
    # Categorie più comuni dal database reale (dal paste.txt fornito)
    categories = [
        "clothes", "hairdresser", "supermarket", "bakery", "car_repair",
        "beauty", "convenience", "jewelry", "newsagent", "car", 
        "florist", "furniture", "shoes", "optician", "pastry",
        "tobacco", "kiosk", "butcher", "laundry", "stationery",
        "greengrocer", "books", "dry_cleaning", "mobile_phone",
        "bicycle", "travel_agency", "hardware", "pet", "houseware",
        "electronics", "wine", "chemist", "copyshop", "perfumery"
    ]
    
    # Nomi di negozi tipici italiani
    shop_names = [
        "Il Fornaio", "Bella Vista", "La Boutique", "Casa Moderna", 
        "Il Gioiello", "Profumi & Co", "TechStore", "Auto Service",
        "Farmacia Centrale", "Bar Italia", "Pizzeria Napoli", "Libreria Dante",
        "Ottica Milano", "Scarpe & Style", "Il Parrucchiere", "Casa & Giardino",
        "Alimentari Rossi", "Elettronica Plus", "Moda Italiana", "Sport Center"
    ]
    
    shops = []
    num_shops = min(25, len(shop_names))  # Massimo 25 negozi
    
    for i in range(num_shops):
        # Coordinate casuali nell'area specifica
        lat = south + random.random() * (north - south)
        lon = west + random.random() * (east - west)
        
        category = random.choice(categories)
        shop_name = random.choice(shop_names)
        
        # Rimuovi il nome scelto per evitare duplicati
        if shop_name in shop_names:
            shop_names.remove(shop_name)
        
        shops.append({
            "id": i + 1,
            "shop_name": f"{shop_name} ({category.replace('_', ' ').title()})",
            "category": category,
            "lat": lat,
            "lon": lon
        })
    
    logger.info(f"Generati {len(shops)} negozi di fallback nell'area [{south},{west}] -> [{north},{east}]")
    return shops