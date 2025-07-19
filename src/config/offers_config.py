"""
Configurazione per il sistema di offerte.
"""
from typing import Dict, List, Tuple
from datetime import timedelta

# Configurazione sconti per categoria
CATEGORY_DISCOUNT_RANGES: Dict[str, Tuple[int, int]] = {
    "ristorante": (10, 25),      # 10-25% di sconto
    "bar": (15, 30),             # 15-30% di sconto  
    "abbigliamento": (20, 40),   # 20-40% di sconto
    "supermercato": (5, 15),     # 5-15% di sconto
    "elettronica": (10, 20),     # 10-20% di sconto
    "farmacia": (5, 10),         # 5-10% di sconto
    "libreria": (15, 25),        # 15-25% di sconto
    "gelateria": (10, 20),       # 10-20% di sconto
    "parrucchiere": (20, 35),    # 20-35% di sconto
    "palestra": (25, 40),        # 25-40% di sconto
}

# Durata offerte per categoria (giorni)
CATEGORY_OFFER_DURATION: Dict[str, Tuple[int, int]] = {
    "ristorante": (7, 21),       # 1-3 settimane
    "bar": (3, 14),              # 3 giorni - 2 settimane
    "abbigliamento": (14, 60),   # 2 settimane - 2 mesi
    "supermercato": (1, 7),      # 1-7 giorni
    "elettronica": (30, 90),     # 1-3 mesi
    "farmacia": (14, 30),        # 2 settimane - 1 mese
    "libreria": (30, 60),        # 1-2 mesi
    "gelateria": (1, 7),         # 1-7 giorni (stagionale)
    "parrucchiere": (14, 30),    # 2 settimane - 1 mese
    "palestra": (30, 90),        # 1-3 mesi
}

# Template descrizioni per categoria
CATEGORY_DESCRIPTIONS: Dict[str, List[str]] = {
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
        "Sconto special su accessori e scarpe!",
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

# Targeting per interessi utente
INTEREST_TARGETING: Dict[str, List[str]] = {
    "ristorante": ["cucina", "cibo", "gastronomia", "wine", "food"],
    "bar": ["caffè", "aperitivo", "socializing", "drink"],
    "abbigliamento": ["moda", "style", "shopping", "fashion", "vestiti"],
    "supermercato": ["casa", "famiglia", "cucina", "spesa"],
    "elettronica": ["tecnologia", "tech", "gadget", "computer", "smartphone"],
    "farmacia": ["salute", "benessere", "cura", "medicina"],
    "libreria": ["lettura", "libri", "cultura", "studio", "books"],
    "gelateria": ["dolci", "gelato", "dessert", "estate"],
    "parrucchiere": ["bellezza", "cura", "estetica", "capelli"],
    "palestra": ["fitness", "sport", "allenamento", "wellness", "body"]
}

# Probabilità di generazione offerta per categoria (0.0-1.0)
CATEGORY_OFFER_PROBABILITY: Dict[str, float] = {
    "ristorante": 0.8,      # Alta probabilità
    "bar": 0.9,             # Molto alta
    "abbigliamento": 0.7,   # Alta
    "supermercato": 0.6,    # Media-alta
    "elettronica": 0.5,     # Media
    "farmacia": 0.4,        # Media-bassa
    "libreria": 0.5,        # Media
    "gelateria": 0.8,       # Alta (stagionale)
    "parrucchiere": 0.6,    # Media-alta
    "palestra": 0.7,        # Alta
}

# Configurazione usi massimi per categoria
CATEGORY_MAX_USES: Dict[str, Tuple[int, int]] = {
    "ristorante": (50, 200),    # 50-200 usi
    "bar": (100, 500),          # 100-500 usi
    "abbigliamento": (20, 100), # 20-100 usi
    "supermercato": (200, 1000), # 200-1000 usi
    "elettronica": (10, 50),    # 10-50 usi
    "farmacia": (100, 300),     # 100-300 usi
    "libreria": (30, 150),      # 30-150 usi
    "gelateria": (100, 400),    # 100-400 usi
    "parrucchiere": (20, 80),   # 20-80 usi
    "palestra": (50, 200),      # 50-200 usi
}

# Configurazione fasce età target per categoria
CATEGORY_AGE_TARGETING: Dict[str, Dict[str, Tuple[int, int]]] = {
    "ristorante": {
        "giovani": (18, 30),
        "adulti": (30, 50),
        "senior": (50, 80)
    },
    "bar": {
        "giovani": (18, 35),
        "adulti": (25, 55)
    },
    "abbigliamento": {
        "giovani": (16, 35),
        "adulti": (25, 50),
        "senior": (45, 70)
    },
    "supermercato": {
        "adulti": (25, 65),
        "senior": (50, 80)
    },
    "elettronica": {
        "giovani": (16, 40),
        "adulti": (25, 60)
    },
    "farmacia": {
        "adulti": (30, 70),
        "senior": (55, 85)
    },
    "libreria": {
        "studenti": (16, 30),
        "adulti": (25, 60),
        "senior": (50, 80)
    },
    "gelateria": {
        "bambini": (5, 16),
        "giovani": (15, 40),
        "famiglie": (25, 50)
    },
    "parrucchiere": {
        "giovani": (16, 40),
        "adulti": (25, 65)
    },
    "palestra": {
        "giovani": (18, 45),
        "adulti": (30, 60)
    }
}

# Numero di offerte da generare per negozio
MIN_OFFERS_PER_SHOP = 1
MAX_OFFERS_PER_SHOP = 3

# Default values
DEFAULT_DISCOUNT_RANGE = (10, 30)
DEFAULT_DURATION_RANGE = (7, 30)
DEFAULT_MAX_USES_RANGE = (50, 200)