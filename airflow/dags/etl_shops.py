# src/etl_shops.py
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import requests
import psycopg2
import logging
import sys
import os

# Aggiungi il percorso del progetto al PYTHONPATH
sys.path.insert(0, '/workspace')

from src.services.offers_service import OffersService

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 4, 12),
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

def extract_data(**kwargs):
    """Estrae dati dei negozi da Overpass API."""
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
    url = "http://overpass-api.de/api/interpreter"
    response = requests.post(url, data={'data': overpass_query})
    response.raise_for_status()
    data = response.json()
    logger.info(f"Estratti {len(data.get('elements', []))} elementi da Overpass API")
    return data.get("elements", [])

def transform_data(**kwargs):
    """Trasforma i dati estratti in formato adatto per il database."""
    ti = kwargs['ti']
    raw_data = ti.xcom_pull(task_ids='extract_data')
    transformed = []
    
    for element in raw_data:
        if element.get("type") == "node":
            lat = element.get("lat")
            lon = element.get("lon")
        elif "center" in element:
            lat = element["center"].get("lat")
            lon = element["center"].get("lon")
        else:
            continue
            
        tags = element.get("tags", {})
        
        transformed.append({
            "name": tags.get("name", "Non specificato"),
            "address": tags.get("addr:full", tags.get("addr:street", "Non specificato")),
            "category": tags.get("shop", "Non specificato"),
            "geom": f"POINT({lon} {lat})"
        })
    
    logger.info(f"Trasformati {len(transformed)} negozi")
    return transformed

def load_data(**kwargs):
    """Carica i dati dei negozi nel database."""
    ti = kwargs['ti']
    shops = ti.xcom_pull(task_ids='transform_data')
    
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO public;")
    
    # Insert query con ON CONFLICT per evitare duplicati
    insert_query = """
      INSERT INTO shops (shop_name, address, category, geom)
      VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
      ON CONFLICT ON CONSTRAINT shops_pkey DO NOTHING
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
            if cur.fetchone():  # Se c'è un RETURNING, il record è stato inserito
                inserted_count += 1
        except Exception as e:
            logger.error(f"Errore inserimento negozio {shop['name']}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"Inseriti {inserted_count} nuovi negozi nel database")
    return inserted_count

def generate_offers(**kwargs):
    """Genera offerte casuali per tutti i negozi."""
    try:
        # Inizializza il servizio offerte
        offers_service = OffersService(POSTGRES_CONFIG)
        
        # Prima pulisce le offerte scadute
        expired_count = offers_service.cleanup_expired_offers()
        logger.info(f"Pulite {expired_count} offerte scadute")
        
        # Poi genera nuove offerte
        offers_count = offers_service.generate_offers_for_all_shops()
        logger.info(f"Generate {offers_count} nuove offerte")
        
        return {
            'expired_cleaned': expired_count,
            'new_offers': offers_count
        }
        
    except Exception as e:
        logger.error(f"Errore nella generazione delle offerte: {e}")
        raise

def validate_data_quality(**kwargs):
    """Valida la qualità dei dati inseriti."""
    ti = kwargs['ti']
    shops_inserted = ti.xcom_pull(task_ids='load_data')
    offers_result = ti.xcom_pull(task_ids='generate_offers')
    
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    cur = conn.cursor()
    
    try:
        # Conta negozi totali
        cur.execute("SELECT COUNT(*) FROM shops")
        total_shops = cur.fetchone()[0]
        
        # Conta offerte attive
        cur.execute("SELECT COUNT(*) FROM offers WHERE is_active = true")
        active_offers = cur.fetchone()[0]
        
        # Verifica negozi senza offerte
        cur.execute("""
            SELECT COUNT(*) FROM shops s 
            LEFT JOIN offers o ON s.shop_id = o.shop_id AND o.is_active = true
            WHERE o.offer_id IS NULL
        """)
        shops_without_offers = cur.fetchone()[0]
        
        # Log statistiche
        logger.info(f"=== STATISTICHE ETL ===")
        logger.info(f"Negozi totali: {total_shops}")
        logger.info(f"Negozi inseriti in questa esecuzione: {shops_inserted}")
        logger.info(f"Offerte attive totali: {active_offers}")
        logger.info(f"Nuove offerte generate: {offers_result.get('new_offers', 0)}")
        logger.info(f"Negozi senza offerte: {shops_without_offers}")
        
        # Controlli di qualità
        if shops_without_offers > total_shops * 0.5:  # Più del 50% senza offerte
            logger.warning(f"Attenzione: {shops_without_offers} negozi non hanno offerte attive")
        
        return {
            'total_shops': total_shops,
            'shops_inserted': shops_inserted,
            'active_offers': active_offers,
            'new_offers': offers_result.get('new_offers', 0),
            'shops_without_offers': shops_without_offers
        }
        
    finally:
        cur.close()
        conn.close()

# Definizione DAG
with DAG(
    'etl_shops',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    description='ETL per negozi e generazione offerte',
    tags=['nearyou', 'etl', 'shops', 'offers']
) as dag:

    # Task 1: Estrazione dati
    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        doc_md="""
        ### Extract Data
        Estrae i dati dei negozi dall'API Overpass per l'area di Milano.
        """
    )

    # Task 2: Trasformazione dati
    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
        doc_md="""
        ### Transform Data  
        Trasforma i dati grezzi in formato adatto per il database PostgreSQL.
        """
    )

    # Task 3: Caricamento dati
    load_task = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        doc_md="""
        ### Load Data
        Carica i negozi trasformati nel database PostgreSQL con PostGIS.
        """
    )

    # Task 4: Generazione offerte
    offers_task = PythonOperator(
        task_id='generate_offers',
        python_callable=generate_offers,
        doc_md="""
        ### Generate Offers
        Genera offerte casuali per tutti i negozi nel database.
        """
    )

    # Task 5: Validazione qualità dati
    validate_task = PythonOperator(
        task_id='validate_data_quality',
        python_callable=validate_data_quality,
        doc_md="""
        ### Validate Data Quality
        Valida la qualità dei dati inseriti e genera statistiche.
        """
    )

    # Definizione dipendenze
    extract_task >> transform_task >> load_task >> offers_task >> validate_task