# ETL Shops & Offers - Versione autonoma per Airflow con supporto categorie inglesi
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta, date
import requests
import psycopg2
import logging
import random
from typing import List, Dict, Any, Optional
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Configurazione database
POSTGRES_CONFIG = {
    'host': 'postgres-postgis',
    'port': 5432,
    'user': 'nearuser',
    'password': 'nearypass',
    'database': 'near_you_shops'
}

# ===== CONFIGURAZIONE OFFERTE COMPLETA (ITALIANO + INGLESE) =====
CATEGORY_DISCOUNT_RANGES = {
    # Categorie originali italiane (mantieni per compatibilità)
    "ristorante": (10, 25), "bar": (15, 30), "abbigliamento": (20, 40),
    "supermercato": (5, 15), "elettronica": (10, 20), "farmacia": (5, 10),
    "libreria": (15, 25), "gelateria": (10, 20), "parrucchiere": (20, 35),
    "palestra": (25, 40),
    
    # Categorie inglesi da Overpass API - TOP CATEGORIE MILANO
    "clothes": (20, 40),        # Abbigliamento - 1,718 negozi
    "hairdresser": (20, 35),    # Parrucchieri - 1,272 negozi  
    "supermarket": (5, 15),     # Supermercati - 748 negozi
    "bakery": (10, 20),         # Panetterie - 600 negozi
    "car_repair": (15, 30),     # Autofficine - 538 negozi
    "beauty": (20, 35),         # Centri estetici - 503 negozi
    "convenience": (5, 15),     # Negozi di convenienza - 433 negozi
    "jewelry": (20, 50),        # Gioiellerie - 331 negozi
    "newsagent": (10, 20),      # Edicole - 294 negozi
    "car": (10, 25),            # Concessionarie auto - 293 negozi
    
    # Altre categorie comuni
    "pharmacy": (5, 10), "butcher": (5, 15), "florist": (15, 30),
    "electronics": (10, 20), "books": (15, 25), "shoes": (15, 35),
    "sports": (20, 30), "toys": (15, 25), "furniture": (15, 35),
    "hardware": (10, 20), "pet": (10, 25), "bicycle": (15, 30),
    "mobile_phone": (10, 20), "optician": (15, 25), "gift": (15, 30),
    "stationery": (10, 25), "wine": (15, 35), "cheese": (10, 25),
    "chocolate": (15, 30), "ice_cream": (10, 20), "coffee": (15, 25),
    "tea": (15, 25), "spices": (10, 20), "organic": (10, 25),
    "health_food": (15, 30), "cosmetics": (15, 35), "perfumery": (20, 40),
    "massage": (25, 40), "tattoo": (20, 35), "locksmith": (15, 25),
    "dry_cleaning": (10, 20), "laundry": (10, 20), "tailor": (15, 30)
}

CATEGORY_OFFER_DURATION = {
    # Categorie italiane
    "ristorante": (7, 21), "bar": (3, 14), "abbigliamento": (14, 60),
    "supermercato": (1, 7), "elettronica": (30, 90), "farmacia": (14, 30),
    "libreria": (30, 60), "gelateria": (1, 7), "parrucchiere": (14, 30),
    "palestra": (30, 90),
    
    # Categorie inglesi - TOP CATEGORIE
    "clothes": (14, 60),        # Abbigliamento: 2 settimane - 2 mesi
    "hairdresser": (14, 30),    # Parrucchieri: 2-4 settimane  
    "supermarket": (1, 7),      # Supermercati: 1-7 giorni
    "bakery": (1, 5),           # Panetterie: 1-5 giorni (fresco)
    "car_repair": (30, 90),     # Autofficine: 1-3 mesi
    "beauty": (14, 30),         # Centri estetici: 2-4 settimane
    "convenience": (1, 7),      # Convenience: 1-7 giorni
    "jewelry": (30, 90),        # Gioiellerie: 1-3 mesi
    "newsagent": (7, 21),       # Edicole: 1-3 settimane
    "car": (30, 90),            # Concessionarie: 1-3 mesi
    
    # Altre categorie
    "pharmacy": (14, 30), "butcher": (1, 3), "florist": (2, 7),
    "electronics": (30, 90), "books": (30, 60), "shoes": (14, 45),
    "sports": (14, 30), "toys": (14, 45), "furniture": (30, 90),
    "hardware": (30, 60), "pet": (14, 30), "bicycle": (30, 60),
    "mobile_phone": (14, 30), "optician": (30, 60), "gift": (14, 45),
    "stationery": (30, 60), "wine": (30, 90), "cheese": (3, 14),
    "chocolate": (14, 30), "ice_cream": (1, 7), "coffee": (7, 21),
    "tea": (30, 60), "spices": (30, 90), "organic": (7, 21),
    "health_food": (14, 30), "cosmetics": (30, 60), "perfumery": (30, 90),
    "massage": (30, 60), "tattoo": (60, 180), "locksmith": (30, 60),
    "dry_cleaning": (14, 30), "laundry": (14, 30), "tailor": (30, 60)
}

CATEGORY_DESCRIPTIONS = {
    # Descrizioni italiane (mantieni)
    "ristorante": [
        "Sconto speciale su tutti i piatti principali!",
        "Offerta aperitivo: ordina e risparmia!",
        "Menu del giorno scontato per te!",
        "Promozione famiglia: mangia con noi!"
    ],
    "bar": [
        "Happy hour prolungato solo per te!",
        "Caffè e cornetto a prezzo speciale!",
        "Aperitivo con sconto esclusivo!",
        "Colazione scontata dalle 7 alle 10!"
    ],
    
    # Descrizioni inglesi - TOP CATEGORIE
    "clothes": [
        "Saldi esclusivi sui capi di stagione!",
        "Sconto speciale su accessori e scarpe!",
        "Promozione weekend: vesti il tuo stile!",
        "Offerta studenti: moda a prezzi giovani!",
        "Look perfetto a prezzi scontati!"
    ],
    "hairdresser": [
        "Bellezza in offerta: trattamenti scontati!",
        "Taglio e piega a prezzo speciale!",
        "Promozione colore: cambia look!",
        "Offerta coppia: bellezza condivisa!",
        "Nuovo stile, nuovo te: sconto esclusivo!"
    ],
    "supermarket": [
        "Spesa smart: risparmia sulla spesa quotidiana!",
        "Offerta freschezza: frutta e verdura scontate!",
        "Promozione famiglia: più compri, più risparmi!",
        "Sconto sera: acquisti dopo le 18!",
        "La tua spesa conveniente è qui!"
    ],
    "bakery": [
        "Pane fresco con sconto speciale!",
        "Dolci della casa a prezzi dolci!",
        "Promozione mattina: colazione scontata!",
        "Offerta famiglia: bontà per tutti!",
        "Sapori autentici a prezzi speciali!"
    ],
    "car_repair": [
        "Officina di fiducia: servizi scontati!",
        "Tagliando auto a prezzo speciale!",
        "Promozione pneumatici: viaggia sicuro!",
        "Offerta revisione: risparmia ora!",
        "La tua auto in perfetta forma!"
    ],
    "beauty": [
        "Centro estetico: bellezza scontata!",
        "Trattamenti viso e corpo in offerta!",
        "Promozione relax: prenditi cura di te!",
        "Offerta benessere: ti meriti il meglio!",
        "Bellezza naturale a prezzi speciali!"
    ],
    "convenience": [
        "Tutto quello che ti serve, scontato!",
        "Comodità e convenienza sotto casa!",
        "Promozione quotidiana: risparmia ogni giorno!",
        "Offerta famiglia: necessità a prezzi giusti!",
        "Il tuo negozio di fiducia!"
    ],
    "jewelry": [
        "Gioielli preziosi a prezzi speciali!",
        "Brillanti offerte per momenti speciali!",
        "Promozione eleganza: scegli il meglio!",
        "Offerta matrimonio: amore scontato!",
        "Lusso accessibile solo per te!"
    ],
    "newsagent": [
        "Edicola di quartiere: sconti su tutto!",
        "Giornali e riviste a prezzo speciale!",
        "Promozione cultura: informati risparmiando!",
        "Offerta studenti: materiali scontati!",
        "La tua edicola di fiducia!"
    ],
    "car": [
        "Concessionaria: auto dei sogni scontate!",
        "Promozione usato garantito!",
        "Offerta finanziamento: guida subito!",
        "Nuova auto, nuovo inizio!",
        "Qualità e affidabilità a prezzi speciali!"
    ],
    
    # Altre categorie
    "pharmacy": [
        "Farmacia di fiducia: salute scontata!",
        "Benessere in offerta: prodotti per la salute!",
        "Promozione vitamine e integratori!",
        "Offerta famiglia: salute conveniente!"
    ],
    "electronics": [
        "Tech sale: tecnologia a prezzi incredibili!",
        "Offerta smartphone e accessori!",
        "Promozione back to school: studia smart!",
        "Weekend tech: sconti su tutti i device!"
    ],
    "books": [
        "Libri in offerta: nutri la tua mente!",
        "Sconto studenti su tutti i testi!",
        "Promozione lettura: bestseller scontati!",
        "Offerta cultura: libri e riviste!"
    ],
    "shoes": [
        "Scarpe di qualità a prezzi scontati!",
        "Promozione comfort: cammina bene!",
        "Offerta stagionale: stile per tutti!",
        "Passi sicuri con i nostri sconti!"
    ],
    "sports": [
        "Articoli sportivi in grande offerta!",
        "Promozione fitness: allenati risparmiando!",
        "Offerta squadra: equipaggiamento scontato!",
        "Sport e benessere a prezzi speciali!"
    ]
}

CATEGORY_OFFER_PROBABILITY = {
    # Probabilità italiane
    "ristorante": 0.8, "bar": 0.9, "abbigliamento": 0.7, "supermercato": 0.6,
    "elettronica": 0.5, "farmacia": 0.4, "libreria": 0.5, "gelateria": 0.8,
    "parrucchiere": 0.6, "palestra": 0.7,
    
    # Probabilità inglesi - TOP CATEGORIE
    "clothes": 0.7,         # Alta (moda)
    "hairdresser": 0.6,     # Media-alta (servizi)
    "supermarket": 0.6,     # Media-alta (necessità)
    "bakery": 0.8,          # Alta (freschezza)
    "car_repair": 0.4,      # Media-bassa (servizi speciali)
    "beauty": 0.7,          # Alta (benessere)
    "convenience": 0.6,     # Media-alta (quotidiano)
    "jewelry": 0.6,         # Media-alta (lusso)
    "newsagent": 0.5,       # Media (tradizionale)
    "car": 0.4,             # Media-bassa (grandi acquisti)
    
    # Altre probabilità
    "pharmacy": 0.4, "butcher": 0.5, "florist": 0.6, "electronics": 0.5,
    "books": 0.5, "shoes": 0.7, "sports": 0.6, "toys": 0.6,
    "furniture": 0.5, "hardware": 0.4, "pet": 0.6, "bicycle": 0.6,
    "mobile_phone": 0.5, "optician": 0.5, "gift": 0.7, "stationery": 0.5,
    "wine": 0.7, "cheese": 0.6, "chocolate": 0.8, "ice_cream": 0.8,
    "coffee": 0.8, "tea": 0.6, "spices": 0.5, "organic": 0.6,
    "health_food": 0.6, "cosmetics": 0.7, "perfumery": 0.7, "massage": 0.7,
    "tattoo": 0.5, "locksmith": 0.3, "dry_cleaning": 0.4, "laundry": 0.4,
    "tailor": 0.5
}

CATEGORY_MAX_USES = {
    # Usi massimi italiani
    "ristorante": (50, 200), "bar": (100, 500), "abbigliamento": (20, 100),
    "supermercato": (200, 1000), "elettronica": (10, 50), "farmacia": (100, 300),
    "libreria": (30, 150), "gelateria": (100, 400), "parrucchiere": (20, 80),
    "palestra": (50, 200),
    
    # Usi massimi inglesi - TOP CATEGORIE
    "clothes": (20, 100),       # Abbigliamento: 20-100 usi
    "hairdresser": (20, 80),    # Parrucchieri: 20-80 usi
    "supermarket": (200, 1000), # Supermercati: 200-1000 usi
    "bakery": (200, 800),       # Panetterie: 200-800 usi
    "car_repair": (30, 150),    # Autofficine: 30-150 usi
    "beauty": (30, 120),        # Centri estetici: 30-120 usi
    "convenience": (150, 600),  # Convenience: 150-600 usi
    "jewelry": (10, 50),        # Gioiellerie: 10-50 usi
    "newsagent": (100, 400),    # Edicole: 100-400 usi
    "car": (5, 30),             # Concessionarie: 5-30 usi
    
    # Altri usi massimi
    "pharmacy": (100, 300), "butcher": (100, 400), "florist": (50, 200),
    "electronics": (10, 50), "books": (30, 150), "shoes": (30, 120),
    "sports": (40, 160), "toys": (25, 100), "furniture": (10, 50),
    "hardware": (40, 200), "pet": (50, 200), "bicycle": (20, 80),
    "mobile_phone": (20, 100), "optician": (30, 120), "gift": (40, 160),
    "stationery": (50, 200), "wine": (30, 150), "cheese": (80, 300),
    "chocolate": (100, 400), "ice_cream": (150, 600), "coffee": (200, 800),
    "tea": (50, 200), "spices": (30, 120), "organic": (60, 250),
    "health_food": (40, 160), "cosmetics": (50, 200), "perfumery": (20, 80),
    "massage": (20, 80), "tattoo": (10, 40), "locksmith": (20, 80),
    "dry_cleaning": (50, 200), "laundry": (60, 250), "tailor": (20, 80)
}

# Defaults
DEFAULT_DISCOUNT_RANGE = (10, 30)
DEFAULT_DURATION_RANGE = (7, 30)
DEFAULT_MAX_USES_RANGE = (50, 200)
MIN_OFFERS_PER_SHOP = 1
MAX_OFFERS_PER_SHOP = 3

# ===== SERVIZIO OFFERTE AUTONOMO =====
class AirflowOffersService:
    """Servizio offerte integrato per Airflow - versione autonoma."""
    
    def __init__(self, postgres_config: Dict[str, Any]):
        self.postgres_config = postgres_config
        
    def get_connection(self):
        """Ottiene connessione PostgreSQL."""
        return psycopg2.connect(**self.postgres_config)
    
    def generate_offers_for_all_shops(self) -> Dict[str, int]:
        """Genera offerte per tutti i negozi nel database."""
        total_offers = 0
        shops_processed = 0
        categories_stats = {}
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Recupera tutti i negozi
                    cur.execute("""
                        SELECT shop_id, shop_name, category 
                        FROM shops 
                        WHERE category IS NOT NULL 
                          AND category != '' 
                          AND category != 'Non specificato'
                    """)
                    shops = cur.fetchall()
                    
                    logger.info(f"🏪 Trovati {len(shops)} negozi validi per generare offerte")
                    
                    for shop in shops:
                        shops_processed += 1
                        category = shop['category'].lower().strip()
                        
                        # Traccia statistiche per categoria
                        if category not in categories_stats:
                            categories_stats[category] = {'total': 0, 'with_offers': 0}
                        categories_stats[category]['total'] += 1
                        
                        offers = self._generate_offers_for_shop(
                            shop['shop_id'], shop['shop_name'], category
                        )
                        
                        if offers:
                            inserted = self._insert_offers(offers)
                            total_offers += inserted
                            if inserted > 0:
                                categories_stats[category]['with_offers'] += 1
                                logger.debug(f"✅ {shop['shop_name']} ({category}): {inserted} offerte")
                        else:
                            logger.debug(f"⏭️ {shop['shop_name']}: saltato per probabilità")
                    
                    # Log statistiche per categoria
                    logger.info("📊 STATISTICHE OFFERTE PER CATEGORIA:")
                    for cat, stats in sorted(categories_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:10]:
                        coverage = (stats['with_offers'] / stats['total'] * 100) if stats['total'] > 0 else 0
                        logger.info(f"   {cat}: {stats['with_offers']}/{stats['total']} ({coverage:.1f}%)")
        
        except Exception as e:
            logger.error(f"❌ Errore generazione offerte: {e}")
            raise
        
        return {
            'total_offers': total_offers,
            'shops_processed': shops_processed,
            'categories_stats': categories_stats
        }
    
    def _generate_offers_for_shop(self, shop_id: int, shop_name: str, category: str) -> List[Dict]:
        """Genera offerte per un singolo negozio."""
        # Normalizza categoria
        category_clean = category.lower().strip()
        
        # Verifica probabilità
        probability = CATEGORY_OFFER_PROBABILITY.get(category_clean, 0.5)
        if random.random() > probability:
            return []
        
        # Numero casuale di offerte
        num_offers = random.randint(MIN_OFFERS_PER_SHOP, MAX_OFFERS_PER_SHOP)
        offers = []
        
        for i in range(num_offers):
            offer = self._create_random_offer(shop_id, shop_name, category_clean)
            if offer:
                offers.append(offer)
        
        return offers
    
    def _create_random_offer(self, shop_id: int, shop_name: str, category: str) -> Optional[Dict]:
        """Crea una singola offerta casuale."""
        try:
            # Sconto basato su categoria
            discount_range = CATEGORY_DISCOUNT_RANGES.get(category, DEFAULT_DISCOUNT_RANGE)
            discount = random.randint(discount_range[0], discount_range[1])
            
            # Durata basata su categoria
            duration_range = CATEGORY_OFFER_DURATION.get(category, DEFAULT_DURATION_RANGE)
            duration_days = random.randint(duration_range[0], duration_range[1])
            
            # Date validità
            valid_from = date.today()
            valid_until = valid_from + timedelta(days=duration_days)
            
            # Descrizione
            descriptions = CATEGORY_DESCRIPTIONS.get(category, [
                f"Offerta speciale da {shop_name}!",
                f"Sconto del {discount}% per te!",
                f"Promozione esclusiva: approfitta ora!"
            ])
            description = random.choice(descriptions)
            
            # Sostituisci placeholder se presenti
            description = description.replace("{discount}", str(discount))
            description = description.replace("{shop_name}", shop_name)
            
            # Usi massimi
            max_uses_range = CATEGORY_MAX_USES.get(category, DEFAULT_MAX_USES_RANGE)
            max_uses = random.randint(max_uses_range[0], max_uses_range[1])
            
            # Targeting età casuale (30% probabilità)
            min_age, max_age = None, None
            if random.random() < 0.3:
                age_ranges = [(18, 30), (25, 45), (35, 65), (50, 75)]
                min_age, max_age = random.choice(age_ranges)
            
            return {
                'shop_id': shop_id,
                'discount_percent': discount,
                'description': description,
                'offer_type': 'percentage',
                'valid_from': valid_from,
                'valid_until': valid_until,
                'is_active': True,
                'max_uses': max_uses,
                'current_uses': 0,
                'min_age': min_age,
                'max_age': max_age,
                'target_categories': None
            }
            
        except Exception as e:
            logger.error(f"❌ Errore creazione offerta per negozio {shop_id}: {e}")
            return None
    
    def _insert_offers(self, offers: List[Dict]) -> int:
        """Inserisce le offerte nel database."""
        if not offers:
            return 0
        
        inserted_count = 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for offer in offers:
                        try:
                            cur.execute("""
                                INSERT INTO offers (
                                    shop_id, discount_percent, description, offer_type,
                                    valid_from, valid_until, is_active, max_uses, current_uses,
                                    min_age, max_age, target_categories
                                ) VALUES (
                                    %(shop_id)s, %(discount_percent)s, %(description)s, %(offer_type)s,
                                    %(valid_from)s, %(valid_until)s, %(is_active)s, %(max_uses)s, %(current_uses)s,
                                    %(min_age)s, %(max_age)s, %(target_categories)s
                                ) ON CONFLICT DO NOTHING
                            """, offer)
                            
                            if cur.rowcount > 0:
                                inserted_count += 1
                            
                        except Exception as e:
                            logger.error(f"❌ Errore inserimento singola offerta: {e}")
                            conn.rollback()
                            continue
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"❌ Errore inserimento batch offerte: {e}")
            raise
        
        return inserted_count
    
    def cleanup_expired_offers(self) -> int:
        """Disattiva le offerte scadute."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE offers 
                        SET is_active = false, updated_at = CURRENT_TIMESTAMP
                        WHERE is_active = true 
                          AND valid_until < CURRENT_DATE
                    """)
                    
                    updated_count = cur.rowcount
                    conn.commit()
                    
                    if updated_count > 0:
                        logger.info(f"🧹 Disattivate {updated_count} offerte scadute")
                    
                    return updated_count
                    
        except Exception as e:
            logger.error(f"❌ Errore cleanup offerte scadute: {e}")
            return 0

# ===== TASK FUNCTIONS =====
def extract_data(**kwargs):
    """Estrae dati dei negozi da Overpass API."""
    logger.info("🔍 Inizio estrazione dati da Overpass API...")
    
    overpass_query = """
    [out:json][timeout:25];
    area["name"="Milano"]->.searchArea;
    (
      node["shop"](area.searchArea);
      way["shop"](area.searchArea);
      relation["shop"](area.searchArea);
    );
    out center;
    """
    
    try:
        url = "http://overpass-api.de/api/interpreter"
        response = requests.post(url, data={'data': overpass_query}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        elements = data.get("elements", [])
        logger.info(f"✅ Estratti {len(elements)} elementi da Overpass API")
        return elements
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Errore chiamata Overpass API: {e}")
        # Fallback: restituisci lista vuota per non bloccare il pipeline
        return []
    except Exception as e:
        logger.error(f"❌ Errore generico estrazione: {e}")
        return []

def transform_data(**kwargs):
    """Trasforma i dati estratti in formato adatto per il database."""
    logger.info("🔄 Inizio trasformazione dati...")
    
    ti = kwargs['ti']
    raw_data = ti.xcom_pull(task_ids='extract_data')
    
    if not raw_data:
        logger.warning("⚠️ Nessun dato da trasformare")
        return []
    
    transformed = []
    skipped = 0
    
    for element in raw_data:
        try:
            # Estrai coordinate
            if element.get("type") == "node":
                lat = element.get("lat")
                lon = element.get("lon")
            elif "center" in element:
                lat = element["center"].get("lat")
                lon = element["center"].get("lon")
            else:
                skipped += 1
                continue
            
            # Verifica coordinate valide
            if not lat or not lon:
                skipped += 1
                continue
                
            tags = element.get("tags", {})
            
            # Pulisci e normalizza i dati
            name = tags.get("name", "").strip()
            if not name:
                name = f"Negozio {tags.get('shop', 'Generico')}"
            
            address = tags.get("addr:full", "").strip()
            if not address:
                address = tags.get("addr:street", "Non specificato").strip()
            
            category = tags.get("shop", "").strip().lower()
            if not category:
                category = "generico"
            
            transformed.append({
                "name": name[:255],  # Limita lunghezza
                "address": address[:500],
                "category": category,
                "geom": f"POINT({lon} {lat})"
            })
            
        except Exception as e:
            logger.error(f"❌ Errore trasformazione elemento: {e}")
            skipped += 1
            continue
    
    logger.info(f"✅ Trasformati {len(transformed)} negozi, saltati {skipped}")
    return transformed

def load_data(**kwargs):
    """Carica i dati dei negozi nel database."""
    logger.info("💾 Inizio caricamento dati nel database...")
    
    ti = kwargs['ti']
    shops = ti.xcom_pull(task_ids='transform_data')
    
    if not shops:
        logger.warning("⚠️ Nessun negozio da inserire")
        return 0
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        cur.execute("SET search_path TO public;")
        
        insert_query = """
          INSERT INTO shops (shop_name, address, category, geom)
          VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
          ON CONFLICT DO NOTHING
          RETURNING shop_id;
        """
        
        inserted_count = 0
        for shop in shops:
            try:
                cur.execute(insert_query, (
                    shop["name"],
                    shop["address"],
                    shop["category"],
                    shop["geom"]
                ))
                if cur.fetchone():
                    inserted_count += 1
            except Exception as e:
                logger.error(f"❌ Errore inserimento negozio {shop['name']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Inseriti {inserted_count} nuovi negozi nel database")
        return inserted_count
        
    except Exception as e:
        logger.error(f"❌ Errore connessione database: {e}")
        raise

def generate_offers(**kwargs):
    """Genera offerte casuali per tutti i negozi."""
    logger.info("🎯 Inizio generazione offerte...")
    
    try:
        offers_service = AirflowOffersService(POSTGRES_CONFIG)
        
        # Cleanup offerte scadute
        expired_count = offers_service.cleanup_expired_offers()
        
        # Genera nuove offerte
        result = offers_service.generate_offers_for_all_shops()
        
        logger.info(f"✅ Generazione completata:")
        logger.info(f"   📊 Negozi processati: {result['shops_processed']}")
        logger.info(f"   🎁 Nuove offerte: {result['total_offers']}")
        logger.info(f"   🧹 Offerte scadute rimosse: {expired_count}")
        
        return {
            'expired_cleaned': expired_count,
            'new_offers': result['total_offers'],
            'shops_processed': result['shops_processed'],
            'categories_stats': result['categories_stats']
        }
        
    except Exception as e:
        logger.error(f"❌ Errore nella generazione delle offerte: {e}")
        raise

def validate_data_quality(**kwargs):
    """Valida la qualità dei dati inseriti."""
    logger.info("✅ Inizio validazione qualità dati...")
    
    ti = kwargs['ti']
    shops_inserted = ti.xcom_pull(task_ids='load_data') or 0
    offers_result = ti.xcom_pull(task_ids='generate_offers') or {}
    
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        cur = conn.cursor()
        
        # Statistiche negozi
        cur.execute("SELECT COUNT(*) FROM shops")
        total_shops = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT category) FROM shops WHERE category IS NOT NULL")
        unique_categories = cur.fetchone()[0]
        
        # Statistiche offerte
        cur.execute("SELECT COUNT(*) FROM offers WHERE is_active = true")
        active_offers = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM shops s 
            LEFT JOIN offers o ON s.shop_id = o.shop_id AND o.is_active = true
            WHERE o.offer_id IS NULL
        """)
        shops_without_offers = cur.fetchone()[0]
        
        # Top categorie con offerte
        cur.execute("""
            SELECT s.category, 
                   COUNT(s.shop_id) as total_shops,
                   COUNT(o.offer_id) as shops_with_offers,
                   ROUND(AVG(o.discount_percent), 1) as avg_discount
            FROM shops s
            LEFT JOIN offers o ON s.shop_id = o.shop_id AND o.is_active = true
            GROUP BY s.category
            ORDER BY total_shops DESC
            LIMIT 10
        """)
        top_categories_with_offers = cur.fetchall()
        
        # Report finale
        logger.info("=" * 60)
        logger.info("📊 REPORT QUALITÀ DATI ETL - OFFERTE AGGIORNATE")
        logger.info("=" * 60)
        logger.info(f"🏪 Negozi totali: {total_shops:,}")
        logger.info(f"📥 Negozi inseriti oggi: {shops_inserted:,}")
        logger.info(f"📂 Categorie uniche: {unique_categories}")
        logger.info(f"🎁 Offerte attive: {active_offers:,}")
        logger.info(f"✨ Nuove offerte oggi: {offers_result.get('new_offers', 0):,}")
        logger.info(f"⚠️ Negozi senza offerte: {shops_without_offers:,}")
        logger.info(f"📈 Coverage offerte: {((active_offers/total_shops)*100):.1f}%")
        
        logger.info("\n🔝 TOP 10 CATEGORIE CON STATISTICHE OFFERTE:")
        for cat, total, with_offers, avg_discount in top_categories_with_offers:
            coverage = (with_offers / total * 100) if total > 0 else 0
            avg_discount_str = f"{avg_discount}%" if avg_discount else "N/A"
            logger.info(f"   {cat:15} | {total:4} negozi | {with_offers:4} offerte | {coverage:5.1f}% | avg {avg_discount_str}")
        
        # Controlli qualità
        warnings = []
        if shops_without_offers > total_shops * 0.5:
            warnings.append(f"Troppi negozi senza offerte: {shops_without_offers:,}/{total_shops:,}")
        
        if active_offers == 0:
            warnings.append("Nessuna offerta attiva trovata")
        
        if active_offers / total_shops < 0.3:
            warnings.append(f"Coverage offerte bassa: {((active_offers/total_shops)*100):.1f}%")
        
        if warnings:
            logger.warning("⚠️ AVVERTIMENTI QUALITÀ:")
            for warning in warnings:
                logger.warning(f"   - {warning}")
        else:
            logger.info("✅ Tutti i controlli qualità superati!")
        
        logger.info("=" * 60)
        
        return {
            'total_shops': total_shops,
            'shops_inserted': shops_inserted,
            'unique_categories': unique_categories,
            'active_offers': active_offers,
            'new_offers': offers_result.get('new_offers', 0),
            'shops_without_offers': shops_without_offers,
            'coverage_percent': (active_offers/total_shops)*100 if total_shops > 0 else 0,
            'top_categories_with_offers': top_categories_with_offers,
            'warnings': warnings
        }
        
    except Exception as e:
        logger.error(f"❌ Errore validazione: {e}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# ===== DAG DEFINITION =====
with DAG(
    'etl_shops',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    description='ETL completo per negozi Milano e generazione offerte automatiche multilingua',
    tags=['nearyou', 'etl', 'shops', 'offers', 'milano', 'multilang'],
    max_active_runs=1,
    doc_md="""
    ## ETL NearYou - Negozi Milano e Offerte (IT/EN)
    
    Questo DAG esegue:
    1. **Extract**: Scarica negozi da Overpass API (Milano)
    2. **Transform**: Pulisce e normalizza i dati (supporta categorie IT/EN)
    3. **Load**: Inserisce negozi in PostgreSQL
    4. **Offers**: Genera offerte casuali per ogni negozio (configurazione multilingua)
    5. **Validate**: Controlla qualità dei dati e coverage offerte
    
    ### Caratteristiche
    -  Supporto categorie italiane e inglesi
    -  Configurazione sconti per categoria specifica  
    -  Targeting età e durata personalizzata
    -  Report qualità con statistiche dettagliate
    
    ### Output Atteso
    - ~14K negozi Milano
    - ~12K offerte (85%+ coverage)
    - Top categorie: clothes, hairdresser, supermarket
    
    ### Frequenza
    - Esecuzione: Giornaliera alle 02:00
    - Durata media: 5-15 minuti
    """
) as dag:

    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md="Estrae dati negozi da Overpass API per Milano"
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md="Trasforma e pulisce i dati per il database (supporto multilang)"
    )

    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        doc_md="Carica i negozi in PostgreSQL con PostGIS"
    )

    offers_task = PythonOperator(
        task_id='generate_offers',
        python_callable=generate_offers,
        doc_md="Genera offerte casuali con configurazione IT/EN per categoria"
    )

    validate_task = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
        doc_md="Valida qualità dati e genera report dettagliato con coverage"
    )

    # Pipeline flow
    extract_task >> transform_task >> load_task >> offers_task >> validate_task