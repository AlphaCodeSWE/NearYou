"""
Modelli Pydantic per request/response nelle API del message generator.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class User(BaseModel):
    """Dati utente per personalizzazione messaggio."""
    age: int = Field(..., description="Età dell'utente")
    profession: str = Field(..., description="Professione dell'utente")
    interests: str = Field(..., description="Interessi dell'utente, separati da virgola")

class POI(BaseModel):
    """Point of Interest - negozio o luogo di interesse."""
    name: str = Field(..., description="Nome del POI")
    category: str = Field(..., description="Categoria del POI (es. ristorante, negozio)")
    description: str = Field("", description="Descrizione aggiuntiva del POI")
    # NUOVO: Aggiunto supporto offerte
    shop_id: Optional[int] = Field(None, description="ID del negozio per recuperare offerte")

class Offer(BaseModel):
    """Offerta disponibile per un negozio."""
    offer_id: int = Field(..., description="ID dell'offerta")
    discount_percent: int = Field(..., description="Percentuale di sconto")
    description: str = Field(..., description="Descrizione dell'offerta")
    valid_until: str = Field(..., description="Data di scadenza dell'offerta")
    max_uses: Optional[int] = Field(None, description="Numero massimo di utilizzi")
    current_uses: int = Field(0, description="Numero di utilizzi attuali")
    is_targeted: bool = Field(False, description="Se l'offerta è targetizzata per l'utente")

class POIWithOffer(BaseModel):
    """POI arricchito con informazioni sull'offerta migliore."""
    name: str = Field(..., description="Nome del POI")
    category: str = Field(..., description="Categoria del POI")
    description: str = Field("", description="Descrizione aggiuntiva del POI")
    shop_id: Optional[int] = Field(None, description="ID del negozio")
    best_offer: Optional[Offer] = Field(None, description="Migliore offerta disponibile")
    offers_count: int = Field(0, description="Numero totale di offerte attive")

class GenerateRequest(BaseModel):
    """Request per generazione messaggio personalizzato."""
    user: User
    poi: POI
    
    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "age": 30,
                    "profession": "Ingegnere",
                    "interests": "tecnologia, viaggi, cucina"
                },
                "poi": {
                    "name": "Caffè Milano",
                    "category": "bar",
                    "description": "Negozio a 50m di distanza",
                    "shop_id": 123
                }
            }
        }

class GenerateWithOfferRequest(BaseModel):
    """Request avanzata per generazione messaggio con offerte esplicite."""
    user: User
    poi: POIWithOffer
    include_all_offers: bool = Field(False, description="Include tutte le offerte, non solo la migliore")
    personalization_level: str = Field("standard", description="Livello personalizzazione: basic, standard, advanced")
    
    class Config:
        schema_extra = {
            "example": {
                "user": {
                    "age": 25,
                    "profession": "Studente",
                    "interests": "moda, shopping, caffè"
                },
                "poi": {
                    "name": "Zara Milano",
                    "category": "clothes", 
                    "shop_id": 456,
                    "best_offer": {
                        "offer_id": 789,
                        "discount_percent": 30,
                        "description": "Saldi esclusivi sui capi di stagione!",
                        "valid_until": "2025-08-15",
                        "max_uses": 100,
                        "current_uses": 23,
                        "is_targeted": True
                    },
                    "offers_count": 2
                },
                "include_all_offers": False,
                "personalization_level": "advanced"
            }
        }

class GenerateResponse(BaseModel):
    """Response con messaggio generato."""
    message: str = Field(..., description="Messaggio personalizzato generato")
    cached: bool = Field(False, description="Indica se il messaggio è stato recuperato dalla cache")
    offer_included: bool = Field(False, description="Indica se il messaggio include un'offerta")
    offer_details: Optional[Offer] = Field(None, description="Dettagli dell'offerta inclusa")
    personalization_score: float = Field(0.0, description="Punteggio di personalizzazione 0-1")
    generation_time_ms: Optional[float] = Field(None, description="Tempo di generazione in millisecondi")
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Ciao! Sei a pochi passi da Zara Milano. Oggi c'è uno sconto del 30% su tutti i capi di stagione, perfetto per rinnovare il guardaroba!",
                "cached": False,
                "offer_included": True,
                "offer_details": {
                    "offer_id": 789,
                    "discount_percent": 30,
                    "description": "Saldi esclusivi sui capi di stagione!",
                    "valid_until": "2025-08-15",
                    "max_uses": 100,
                    "current_uses": 23,
                    "is_targeted": True
                },
                "personalization_score": 0.85,
                "generation_time_ms": 1250.5
            }
        }

class HealthResponse(BaseModel):
    """Risposta per health check."""
    status: str = "ok"
    version: str = "1.0.0"
    provider: str = Field(..., description="Provider LLM in uso")
    offers_integration: bool = Field(True, description="Stato integrazione offerte")

class CacheStats(BaseModel):
    """Statistiche della cache."""
    enabled: bool
    hits: Optional[int] = None
    misses: Optional[int] = None
    total: Optional[int] = None
    hit_rate: Optional[float] = None
    cache_info: Optional[dict] = None
    offers_cached: Optional[int] = Field(None, description="Numero offerte in cache")

class OffersStatsResponse(BaseModel):
    """Statistiche sulle offerte disponibili."""
    total_active_offers: int = Field(..., description="Numero totale offerte attive")
    offers_by_category: Dict[str, int] = Field(..., description="Offerte per categoria")
    avg_discount_percent: float = Field(..., description="Sconto medio percentuale")
    top_discounts: list = Field(..., description="Top 5 sconti più alti")
    expiring_soon: int = Field(..., description="Offerte in scadenza entro 7 giorni")