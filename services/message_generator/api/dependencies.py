"""
Dipendenze condivise per il servizio message_generator.
"""
import os
import logging
from typing import Callable, Any, Dict

from langchain.chat_models import ChatOpenAI
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Configurazione LLM
PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
BASE_URL = os.getenv("OPENAI_API_BASE") or None
API_KEY = os.getenv("OPENAI_API_KEY")

# Configurazione PostgreSQL per offerte
POSTGRES_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "postgres-postgis"),
    'port': int(os.getenv("POSTGRES_PORT", "5432")),
    'user': os.getenv("POSTGRES_USER", "nearuser"),
    'password': os.getenv("POSTGRES_PASSWORD", "nearypass"),
    'database': os.getenv("POSTGRES_DB", "near_you_shops")
}

def get_llm_client() -> ChatOpenAI:
    """
    Fornisce un client LLM configurato.
    
    Returns:
        ChatOpenAI: Client configurato per interagire con il modello LLM
    
    Raises:
        RuntimeError: Se la configurazione è mancante
    """
    if PROVIDER in {"openai", "groq", "together", "fireworks"} and not API_KEY:
        raise RuntimeError("OPENAI_API_KEY mancante per il provider scelto")
    
    # Seleziona il modello in base al provider
    if PROVIDER == "openai":
        model_name = "gpt-4o-mini"
    elif PROVIDER == "groq":
        model_name = "gemma2-9b-it"
    else:
        model_name = "gpt-3.5-turbo"  # Default fallback
    
    logger.info(f"Inizializzazione LLM client con provider: {PROVIDER}, modello: {model_name}")
    
    return ChatOpenAI(
        model=model_name,
        temperature=0.7,
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
    )

def get_postgres_connection():
    """
    Fornisce una connessione PostgreSQL per accedere alle offerte.
    
    Returns:
        psycopg2.connection: Connessione al database PostgreSQL
    """
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        logger.debug("Connessione PostgreSQL stabilita per recupero offerte")
        return conn
    except Exception as e:
        logger.error(f"Errore connessione PostgreSQL: {e}")
        raise

def get_prompt_template():
    """Template migliorato per includere meglio le offerte."""
    return """Sei un sistema di advertising che crea un messaggio conciso e coinvolgente per attirare clienti.

Utente:
- Età: {age}
- Professione: {profession}  
- Interessi: {interests}

Negozio:
- Nome: {name}
- Categoria: {category}
- Descrizione: {description}

{offer_section}

Contesto:
- L'utente è a pochi metri dal negozio.
- Il messaggio deve essere breve (max 40 parole) e invogliare l'utente a fermarsi.
- Se c'è un'offerta con sconto, DEVI menzionare la percentuale nel messaggio.
- Usa un tono amichevole e personalizzato.
- Scrivi in italiano.

Genera il messaggio personalizzato che include lo sconto se presente:"""

def get_offer_section_template():
    """
    Restituisce il template per la sezione offerte nel prompt.
    
    Returns:
        str: Template per la sezione offerte
    """
    return """Offerta Speciale Disponibile:
- Sconto: {discount_percent}% 
- Descrizione: {offer_description}
- Validità: fino al {valid_until}
- Utilizzi rimasti: {remaining_uses}"""

def get_no_offer_section():
    """
    Restituisce il testo da usare quando non ci sono offerte.
    
    Returns:
        str: Testo per assenza offerte
    """
    return "Offerta: Nessuna offerta speciale al momento, ma il negozio offre prodotti/servizi di qualità."