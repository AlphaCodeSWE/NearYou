#!/usr/bin/env python3
"""
Script per generare dati di visite campione per testare i grafici di Grafana.
Questo script popola la tabella user_visits con dati realistici per testing.
"""
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import argparse

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as CHError

from src.utils.db_utils import wait_for_clickhouse_database
from src.utils.logger_config import setup_logging
from src.configg import (
    CLICKHOUSE_HOST, CLICKHOUSE_USER,
    CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT,
    CLICKHOUSE_DATABASE
)

setup_logging()
logger = logging.getLogger(__name__)

# Configurazioni per la generazione dei dati
SHOP_CATEGORIES = [
    'ristorante', 'bar', 'supermercato', 'abbigliamento', 
    'elettronica', 'farmacia', 'libreria', 'gelateria', 
    'parrucchiere', 'palestra'
]

SHOP_NAMES = {
    'ristorante': ['Trattoria da Mario', 'Ristorante Il Convivio', 'Osteria del Borgo', 'Pizzeria Napoli'],
    'bar': ['Bar Centrale', 'Caffè Milano', 'Bar Sport', 'Caffè della Piazza'],
    'supermercato': ['Carrefour Express', 'Coop', 'Esselunga', 'Conad'],
    'abbigliamento': ['Zara', 'H&M', 'Boutique Elegant', 'Fashion Store'],
    'elettronica': ['MediaWorld', 'Euronics', 'Tech Shop', 'Apple Store'],
    'farmacia': ['Farmacia Centrale', 'Farmacia San Marco', 'Farmacia del Corso'],
    'libreria': ['Libreria Mondadori', 'Feltrinelli', 'Libreria Universitaria'],
    'gelateria': ['Grom', 'Venchi', 'Gelateria Artigianale', 'Ice Dreams'],
    'parrucchiere': ['Salon Bellezza', 'Hair Style', 'Parrucchieri Moderni'],
    'palestra': ['Fitness Club', 'Body Building Gym', 'Wellness Center']
}

DURATION_RANGES = {
    'ristorante': (30, 120),
    'bar': (10, 30),
    'supermercato': (15, 45),
    'abbigliamento': (20, 60),
    'elettronica': (25, 90),
    'farmacia': (5, 15),
    'libreria': (15, 45),
    'gelateria': (5, 20),
    'parrucchiere': (45, 120),
    'palestra': (60, 150),
}

SPENDING_RANGES = {
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

def get_clickhouse_client() -> Client:
    """Crea e restituisce un client ClickHouse."""
    return Client(
        host=CLICKHOUSE_HOST,
        user=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        port=CLICKHOUSE_PORT,
        database=CLICKHOUSE_DATABASE
    )

def get_existing_users(client: Client) -> List[Tuple[int, int, str, str]]:
    """Recupera gli utenti esistenti dal database."""
    try:
        result = client.execute(
            "SELECT user_id, age, profession, interests FROM nearyou.users ORDER BY user_id"
        )
        logger.info(f"Trovati {len(result)} utenti esistenti")
        return result
    except CHError as e:
        logger.error(f"Errore nel recuperare utenti: {e}")
        return []

def generate_visit_data(
    user_id: int, 
    user_age: int, 
    user_profession: str, 
    user_interests: str,
    days_back: int = 30
) -> List[Tuple]:
    """Genera dati di visite per un singolo utente negli ultimi N giorni."""
    visits = []
    
    # Numero di visite per utente (varia in base all'età e professione)
    if user_age < 25:
        base_visits = random.randint(8, 15)  # Giovani più attivi
    elif user_age < 40:
        base_visits = random.randint(5, 12)  # Adulti moderatamente attivi
    else:
        base_visits = random.randint(3, 8)   # Meno visite per età maggiore
    
    # Modifica in base alla professione
    if user_profession in ["Studente", "Giornalista"]:
        base_visits += random.randint(2, 5)  # Più visite per certe professioni
    
    num_visits = min(base_visits, days_back * 2)  # Cap a 2 visite/giorno max
    
    for visit_num in range(num_visits):
        # Data casuale negli ultimi N giorni
        days_ago = random.randint(0, days_back)
        visit_date = datetime.now() - timedelta(days=days_ago)
        
        # Ora casuale durante il giorno (più probabilità in certi orari)
        hour_weights = [1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 8, 7, 6, 5, 4, 8, 9, 7, 5, 3, 2]
        hour = random.choices(range(24), weights=hour_weights)[0]
        minute = random.randint(0, 59)
        
        visit_start = visit_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Scegli categoria negozio in base agli interessi
        category = random.choice(SHOP_CATEGORIES)
        if "caffè" in user_interests.lower():
            category = random.choice(['bar', 'ristorante', category])
        elif "sport" in user_interests.lower():
            category = random.choice(['palestra', 'abbigliamento', category])
        elif "tecnologia" in user_interests.lower():
            category = random.choice(['elettronica', 'libreria', category])
        
        # Nome negozio
        shop_name = random.choice(SHOP_NAMES[category])
        
        # Durata visita
        duration_range = DURATION_RANGES[category]
        duration_minutes = random.randint(duration_range[0], duration_range[1])
        visit_end = visit_start + timedelta(minutes=duration_minutes)
        
        # Probabilità di accettare offerta
        offer_accepted = random.random() < 0.65  # 65% accetta
        
        # Spesa stimata
        spending_range = SPENDING_RANGES[category]
        base_spending = random.uniform(spending_range[0], spending_range[1])
        
        # Modifica spesa in base all'età e giorno della settimana
        if visit_start.weekday() >= 5:  # Weekend
            base_spending *= random.uniform(1.1, 1.4)
        if user_age > 45:  # Maggiore potere d'acquisto
            base_spending *= random.uniform(1.2, 1.5)
        
        estimated_spending = round(base_spending, 2)
        
        # Soddisfazione (generalmente alta)
        satisfaction = random.choices(
            range(1, 11), 
            weights=[1, 1, 2, 3, 5, 8, 12, 15, 20, 25]  # Più peso ai voti alti
        )[0]
        
        # Genera ID univoci
        visit_id = random.randint(100000, 999999)
        shop_id = random.randint(1, 500)
        offer_id = random.randint(1, 100) if offer_accepted else 0
        
        visit_data = (
            visit_id,
            user_id,
            shop_id,
            offer_id,
            visit_start,
            visit_end,
            duration_minutes,
            offer_accepted,
            estimated_spending,
            satisfaction,
            visit_start.weekday() + 1,  # day_of_week (1=Monday)
            visit_start.hour,          # hour_of_day
            "",                        # weather_condition
            user_age,
            user_profession,
            user_interests,
            shop_name,
            category,
            datetime.now()  # created_at
        )
        
        visits.append(visit_data)
    
    return visits

def insert_sample_visits(client: Client, num_days: int = 30, max_users: int = None):
    """Inserisce dati di visite campione nel database."""
    logger.info(f"Inizio generazione dati visite per gli ultimi {num_days} giorni")
    
    # Recupera utenti esistenti
    users = get_existing_users(client)
    if not users:
        logger.error("Nessun utente trovato nel database. Esegui prima generate_users.py")
        return
    
    # Limita il numero di utenti se specificato
    if max_users:
        users = users[:max_users]
    
    logger.info(f"Generazione visite per {len(users)} utenti")
    
    all_visits = []
    for user_id, age, profession, interests in users:
        user_visits = generate_visit_data(user_id, age, profession, interests, num_days)
        all_visits.extend(user_visits)
        
        if len(all_visits) % 100 == 0:
            logger.info(f"Generate {len(all_visits)} visite finora...")
    
    logger.info(f"Inserimento di {len(all_visits)} visite nel database...")
    
    # Inserimento in batch per performance
    batch_size = 500
    for i in range(0, len(all_visits), batch_size):
        batch = all_visits[i:i + batch_size]
        
        try:
            client.execute("""
                INSERT INTO nearyou.user_visits (
                    visit_id, user_id, shop_id, offer_id, visit_start_time, visit_end_time,
                    duration_minutes, offer_accepted, estimated_spending, user_satisfaction,
                    day_of_week, hour_of_day, weather_condition, user_age, user_profession,
                    user_interests, shop_name, shop_category, created_at
                ) VALUES
            """, batch)
            
            logger.info(f"Inserito batch {i//batch_size + 1}/{(len(all_visits) + batch_size - 1)//batch_size}")
            
        except CHError as e:
            logger.error(f"Errore inserimento batch: {e}")
            raise
    
    logger.info(f"✅ Inserite {len(all_visits)} visite campione!")
    
    # Statistiche finali
    total_revenue = sum(visit[8] for visit in all_visits)  # estimated_spending
    avg_duration = sum(visit[6] for visit in all_visits) / len(all_visits)  # duration_minutes
    conversion_rate = sum(1 for visit in all_visits if visit[7]) / len(all_visits) * 100  # offer_accepted
    
    logger.info(f"📊 Statistiche generate:")
    logger.info(f"   - Revenue totale: €{total_revenue:.2f}")
    logger.info(f"   - Durata media: {avg_duration:.1f} minuti")
    logger.info(f"   - Tasso conversione: {conversion_rate:.1f}%")

def clear_existing_visits(client: Client):
    """Cancella visite esistenti (per testing)."""
    try:
        client.execute("TRUNCATE TABLE nearyou.user_visits")
        logger.info("🗑️ Visite esistenti cancellate")
    except CHError as e:
        logger.error(f"Errore cancellazione visite: {e}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Genera dati di visite campione per testing Grafana')
    parser.add_argument('--days', '-d', type=int, default=30,
                       help='Numero di giorni di storico da generare (default: 30)')
    parser.add_argument('--max-users', '-u', type=int, default=None,
                       help='Massimo numero di utenti da considerare (default: tutti)')
    parser.add_argument('--clear', '-c', action='store_true',
                       help='Cancella visite esistenti prima di generare nuove')
    
    args = parser.parse_args()
    
    try:
        client = get_clickhouse_client()
        
        # Attendi che il database sia pronto
        wait_for_clickhouse_database(client, CLICKHOUSE_DATABASE)
        
        # Cancella dati esistenti se richiesto
        if args.clear:
            clear_existing_visits(client)
        
        # Genera nuovi dati
        insert_sample_visits(client, args.days, args.max_users)
        
        logger.info("✅ Generazione dati completata! Controlla i dashboard Grafana.")
        
    except Exception as e:
        logger.error(f"❌ Errore durante la generazione: {e}")
        exit(1)
