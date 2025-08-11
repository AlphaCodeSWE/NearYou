#!/usr/bin/env python3
import random
import time
import argparse
from datetime import datetime, date
import logging

from clickhouse_driver import Client
from clickhouse_driver.errors import Error as CHError
from faker import Faker

from src.utils.db_utils import wait_for_clickhouse_database
from src.utils.logger_config import setup_logging
from src.configg import (
    CLICKHOUSE_HOST, CLICKHOUSE_USER,
    CLICKHOUSE_PASSWORD, CLICKHOUSE_PORT,
    CLICKHOUSE_DATABASE
)

setup_logging()
logger = logging.getLogger(__name__)

NUM_USERS = 5  # default quanti utenti creare

# ——————————————————————————————————————————————————————————————
# Elenchi verosimili
PROFESSIONS = [
    "Ingegnere", "Medico", "Avvocato", "Insegnante",
    "Commercialista", "Architetto", "Farmacista",
    "Giornalista", "Psicologo", "Ricercatore"
]

INTERESTS = [
    "caffè", "bicicletta", "arte", "cinema",
    "fitness", "lettura", "fotografia", "musica",
    "viaggi", "cucina", "sport", "tecnologia"
]

ITALIAN_CITIES = [
    "Milano", "Roma", "Torino", "Napoli", "Bologna",
    "Firenze", "Genova", "Venezia", "Verona", "Palermo"
]

EMAIL_DOMAINS = [
    "gmail.com", "libero.it", "hotmail.it", "yahoo.it",
    "alice.it", "tiscali.it"
]

# ——————————————————————————————————————————————————————————————
# Faker per nome/cognome e telefono
fake = Faker('it_IT')

# ClickHouse client
client = Client(
    host=CLICKHOUSE_HOST,
    user=CLICKHOUSE_USER,
    password=CLICKHOUSE_PASSWORD,
    port=CLICKHOUSE_PORT,
    database=CLICKHOUSE_DATABASE
)

def wait_for_table(table_name: str, timeout: int = 2, max_retries: int = 30) -> bool:
    retries = 0
    while retries < max_retries:
        try:
            tables = [t[0] for t in client.execute("SHOW TABLES")]
            if table_name in tables:
                logger.info("La tabella '%s' è disponibile.", table_name)
                return True
        except CHError as e:
            logger.error("Errore controllo tabella '%s': %s", table_name, e)
        time.sleep(timeout)
        retries += 1
    raise Exception(f"Tabella '{table_name}' non trovata dopo {max_retries} tentativi.")

def calculate_age(birthdate: date) -> int:
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

def get_max_user_id() -> int:
    """Ottiene il massimo user_id esistente nella tabella users."""
    try:
        result = client.execute("SELECT max(user_id) FROM users")
        max_id = result[0][0] if result and result[0][0] is not None else 0
        logger.info(f"Massimo user_id esistente: {max_id}")
        return max_id
    except CHError as e:
        logger.warning(f"Errore nel recuperare max user_id (tabella potrebbe essere vuota): {e}")
        return 0

def check_existing_user_ids(start_id: int, end_id: int) -> set:
    """Controlla quali user_id esistono già nel range specificato."""
    try:
        result = client.execute(
            "SELECT user_id FROM users WHERE user_id >= %(start)s AND user_id <= %(end)s",
            {"start": start_id, "end": end_id}
        )
        existing_ids = {row[0] for row in result}
        if existing_ids:
            logger.info(f"Trovati {len(existing_ids)} user_id esistenti nel range {start_id}-{end_id}")
        return existing_ids
    except CHError as e:
        logger.warning(f"Errore nel controllare user_id esistenti: {e}")
        return set()

def check_existing_usernames_emails() -> tuple[set, set]:
    """Controlla username e email già esistenti per evitare duplicati."""
    try:
        result = client.execute("SELECT username, email FROM users")
        existing_usernames = {row[0] for row in result}
        existing_emails = {row[1] for row in result}
        logger.info(f"Trovati {len(existing_usernames)} username e {len(existing_emails)} email esistenti")
        return existing_usernames, existing_emails
    except CHError as e:
        logger.warning(f"Errore nel controllare username/email esistenti: {e}")
        return set(), set()

def generate_unique_username_email(existing_usernames: set, existing_emails: set) -> tuple[str, str]:
    """Genera username ed email unici."""
    max_attempts = 100
    
    for attempt in range(max_attempts):
        # Nome e cognome verosimili
        full_name = fake.name()
        first, last = full_name.split(" ", 1)
        
        # Username: first + last lowercase + numero se necessario
        base_username = (first + last).lower().replace("'", "").replace(" ", "")
        username = base_username
        if username in existing_usernames:
            username = f"{base_username}{random.randint(1, 9999)}"
        
        # Email basata su username e dominio casuale
        email = f"{username}@{random.choice(EMAIL_DOMAINS)}"
        
        # Verifica unicità
        if username not in existing_usernames and email not in existing_emails:
            existing_usernames.add(username)  # Aggiorna per i prossimi utenti
            existing_emails.add(email)
            return username, email, full_name
    
    raise Exception(f"Impossibile generare username/email unici dopo {max_attempts} tentativi")

def generate_user_record(user_id: int, existing_usernames: set, existing_emails: set) -> tuple:
    # Genera username ed email unici
    username, email, full_name = generate_unique_username_email(existing_usernames, existing_emails)
    
    # Sesso e data di nascita Faker
    profile = fake.simple_profile()
    gender = "Male" if profile["sex"] == "M" else "Female"
    birthdate = profile["birthdate"]
    age = calculate_age(birthdate)

    # Campi da elenchi definiti
    profession = random.choice(PROFESSIONS)
    interests = ", ".join(random.sample(INTERESTS, k=3))
    country = "Italia"
    city = random.choice(ITALIAN_CITIES)

    # Contatto e credenziali
    phone_number = fake.phone_number()
    password = fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)

    # Tipo utente
    user_type = random.choice(["free", "premium"])

    # Timestamp di registrazione
    registration_time = datetime.now()

    return (
        user_id,
        username,
        full_name,
        email,
        phone_number,
        password,
        user_type,
        gender,
        age,
        profession,
        interests,
        country,
        city,
        registration_time
    )

def insert_users(num_users: int):
    logger.info("Generazione di %d utenti verosimili...", num_users)
    
    # Ottieni il massimo user_id esistente per evitare conflitti
    max_existing_id = get_max_user_id()
    start_id = max_existing_id + 1
    end_id = start_id + num_users - 1
    
    # Doppio controllo: verifica se alcuni ID nel range esistono già
    existing_ids = check_existing_user_ids(start_id, end_id)
    
    # Ottieni username ed email esistenti per evitare duplicati
    existing_usernames, existing_emails = check_existing_usernames_emails()
    
    # Genera gli utenti partendo dal primo ID sicuro
    records = []
    current_id = start_id
    
    for i in range(num_users):
        # Salta gli ID che esistono già (failsafe)
        while current_id in existing_ids:
            current_id += 1
            
        records.append(generate_user_record(current_id, existing_usernames, existing_emails))
        current_id += 1
    
    logger.info(f"Inserimento utenti con ID da {start_id} a {current_id-1}")
    
    query = """
        INSERT INTO users (
            user_id, username, full_name, email, phone_number,
            password, user_type, gender, age, profession,
            interests, country, city, registration_time
        ) VALUES
    """
    try:
        client.execute(query, records)
        logger.info("Inseriti %d utenti nella tabella 'users'.", len(records))
        logger.info(f"Range di user_id inseriti: {records[0][0]} - {records[-1][0]}")
    except CHError as e:
        logger.error("Errore inserimento utenti: %s", e)
        raise

if __name__ == '__main__':
    # Parsing argomenti da linea di comando
    parser = argparse.ArgumentParser(description='Genera utenti verosimili per ClickHouse')
    parser.add_argument('--num-users', '-n', type=int, default=NUM_USERS,
                       help=f'Numero di utenti da generare (default: {NUM_USERS})')
    parser.add_argument('--check-duplicates', action='store_true',
                       help='Esegui controlli estesi per evitare duplicati')
    args = parser.parse_args()
    
    try:
        # 1) Attendi che il DB e la tabella siano pronti
        wait_for_clickhouse_database(client, CLICKHOUSE_DATABASE)
        wait_for_table("users")

        # 2) Inserisci i profili
        logger.info(f"Avvio generazione di {args.num_users} utenti...")
        insert_users(args.num_users)
        logger.info("Operazione completata con successo.")
        
    except Exception as e:
        logger.error(f"Errore durante la generazione utenti: {e}")
        exit(1)