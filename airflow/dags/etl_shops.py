# ETL Shops & Offers - Versione autonoma per Airflow
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

# ===== CONFIGURAZIONE OFFERTE COMPLETA =====
CATEGORY_DISCOUNT_RANGES = {
    "ristorante": (10, 25), "bar": (15, 30), "abbigliamento": (20, 40),
    "supermercato": (5, 15), "elettronica": (10, 20), "farmacia": (5, 10),
    "libreria": (15, 25), "gelateria": (10, 20), "parrucchiere": (20, 35),
    "palestra": (25, 40), "shoes": (15, 35), "jewelry": (20, 50),
    "bakery": (10, 20), "butcher": (5, 15), "florist": (15, 30)
}

CATEGORY_OFFER_DURATION = {
    "ristorante": (7, 21), "bar": (3, 14), "abbigliamento": (14, 60),
    "supermercato": (1, 7), "elettronica": (30, 90), "farmacia": (14, 30),
    "libreria": (30, 60), "gelateria": (1, 7), "parrucchiere": (14, 30),
    "palestra": (30, 90), "shoes": (14, 45), "jewelry": (30, 90),
    "bakery": (1, 5), "butcher": (1, 3), "florist": (2, 7)
}

CATEGORY_DESCRIPTIONS = {
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
    "abbigliamento": [
        "Saldi esclusivi sui capi di stagione!",
        "Sconto speciale su accessori e scarpe!",
        "Promozione weekend: vesti il tuo stile!",
        "Offerta studenti: moda a prezzi giovani!"
    ],
    "supermercato": [
        "Spesa smart: risparmia sulla spesa quotidiana!",
        "Offerta freschezza: frutta e verdura scontate!",
        "Promozione famiglia: più compri, più risparmi!",
        "Sconto sera: acquisti dopo le 18!"
    ],
    "elettronica": [
        "Tech sale: tecnologia a prezzi incredibili!",
        "Offerta smartphone e accessori!",
        "Promozione back to school: studia smart!",
        "Weekend tech: sconti su tutti i device!"
    ],
    "farmacia": [
        "Benessere in offerta: prodotti per la salute!",
        "Sconto cosmetica e igiene personale!",
        "Promozione vitamine e integratori!",
        "Offerta famiglia: salute conveniente!"
    ],
    "libreria": [
        "Libri in offerta: nutri la tua mente!",
        "Sconto studenti su tutti i testi!",
        "Promozione lettura: bestseller scontati!",
        "Offerta cultura: libri e riviste!"
    ],
    "gelateria": [
        "Gelato fresco con sconto speciale!",
        "Happy hour gelato: rinfrescati con noi!",
        "Promozione famiglia: gusti per tutti!",
        "Offerta estate: gelato a prezzi cool!"
    ],
    "parrucchiere": [
        "Bellezza in offerta: trattamenti scontati!",
        "Taglio e piega a prezzo speciale!",
        "Promozione colore: cambia look!",
        "Offerta coppia: bellezza condivisa!"
    ],
    "palestra": [
        "Fitness in offerta: allena il tuo corpo!",
        "Prova gratuita + sconto abbonamento!",
        "Promozione estate: forma fisica top!",
        "Offerta studenti: sport accessibile!"
    ]
}

CATEGORY_OFFER_PROBABILITY = {
    "ristorante": 0.8, "bar": 0.9, "abbigliamento": 0.7, "supermercato": 0.6,
    "elettronica": 0.5, "farmacia": 0.4, "libreria": 0.5, "gelateria": 0.8,
    "parrucchiere": 0.6, "palestra": 0.7, "shoes": 0.7, "jewelry": 0.6,
    "bakery": 0.8, "butcher": 0.5, "florist": 0.6
}

CATEGORY_MAX_USES = {
    "ristorante": (50, 200), "bar": (100, 500), "abbigliamento": (20, 100),
    "supermercato": (200, 1000), "elettronica": (10, 50), "farmacia": (100, 300),
    "libreria": (30, 150), "gelateria": (100, 400), "parrucchiere": (20, 80),
    "palestra": (50, 200), "shoes": (30, 120), "jewelry": (10, 50),
    "bakery": (200, 800), "butcher": (100, 400), "florist": (50, 200)
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
                    
                    logger.info(f"Trovati {len(shops)} negozi validi per generare offerte")
                    
                    for shop in shops:
                        shops_processed += 1
                        offers = self._generate_offers_for_shop(
                            shop['shop_id'], shop['shop_name'], shop['category']
                        )
                        
                        if offers:
                            inserted = self._insert_offers(offers)
                            total_offers += inserted
                            if inserted > 0:
                                logger.info(f"✅ {shop['shop_name']} ({shop['category']}): {inserted} offerte")
                        else:
                            logger.debug(f"⏭️ {shop['shop_name']}: saltato per probabilità")
        
        except Exception as e:
            logger.error(f"❌ Errore generazione offerte: {e}")
            raise
        
        return {
            'total_offers': total_offers,
            'shops_processed': shops_processed
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
            'shops_processed': result['shops_processed']
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
        
        # Top categorie
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM shops 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_categories = cur.fetchall()
        
        # Report finale
        logger.info("=" * 50)
        logger.info("📊 REPORT QUALITÀ DATI ETL")
        logger.info("=" * 50)
        logger.info(f"🏪 Negozi totali: {total_shops}")
        logger.info(f"📥 Negozi inseriti oggi: {shops_inserted}")
        logger.info(f"📂 Categorie uniche: {unique_categories}")
        logger.info(f"🎁 Offerte attive: {active_offers}")
        logger.info(f"✨ Nuove offerte oggi: {offers_result.get('new_offers', 0)}")
        logger.info(f"⚠️ Negozi senza offerte: {shops_without_offers}")
        
        logger.info("\n🔝 TOP 5 CATEGORIE:")
        for cat, count in top_categories:
            logger.info(f"   {cat}: {count} negozi")
        
        # Controlli qualità
        warnings = []
        if shops_without_offers > total_shops * 0.5:
            warnings.append(f"Troppi negozi senza offerte: {shops_without_offers}/{total_shops}")
        
        if active_offers == 0:
            warnings.append("Nessuna offerta attiva trovata")
        
        if warnings:
            logger.warning("⚠️ AVVERTIMENTI QUALITÀ:")
            for warning in warnings:
                logger.warning(f"   - {warning}")
        else:
            logger.info("✅ Tutti i controlli qualità superati!")
        
        logger.info("=" * 50)
        
        return {
            'total_shops': total_shops,
            'shops_inserted': shops_inserted,
            'unique_categories': unique_categories,
            'active_offers': active_offers,
            'new_offers': offers_result.get('new_offers', 0),
            'shops_without_offers': shops_without_offers,
            'top_categories': top_categories,
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
    description='ETL completo per negozi e generazione offerte automatiche',
    tags=['nearyou', 'etl', 'shops', 'offers', 'milano'],
    max_active_runs=1,
    doc_md="""
    ## ETL NearYou - Negozi e Offerte
    
    Questo DAG esegue:
    1. **Extract**: Scarica negozi da Overpass API (Milano)
    2. **Transform**: Pulisce e normalizza i dati
    3. **Load**: Inserisce negozi in PostgreSQL
    4. **Offers**: Genera offerte casuali per ogni negozio
    5. **Validate**: Controlla qualità dei dati
    
    ### Frequenza
    - Esecuzione: Giornaliera
    - Durata media: 5-10 minuti
    
    ### Output
    - Negozi inseriti in tabella `shops`
    - Offerte generate in tabella `offers`
    - Report qualità nei log
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
        doc_md="Trasforma e pulisce i dati per il database"
    )

    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        doc_md="Carica i negozi in PostgreSQL con PostGIS"
    )

    offers_task = PythonOperator(
        task_id='generate_offers',
        python_callable=generate_offers,
        doc_md="Genera offerte casuali per tutti i negozi"
    )

    validate_task = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
        doc_md="Valida qualità dati e genera report"
    )

    # Pipeline flow
    extract_task >> transform_task >> load_task >> offers_task >> validate_task