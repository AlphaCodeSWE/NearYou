"""
Router per le API del message generator con supporto offerte.
"""
import os
import logging
import time
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from langchain.chat_models import ChatOpenAI

from .models import (
    GenerateRequest, GenerateWithOfferRequest, GenerateResponse, 
    HealthResponse, CacheStats, OffersStatsResponse, Offer, POIWithOffer
)
from .dependencies import (
    get_llm_client, get_postgres_connection, get_prompt_template,
    get_offer_section_template, get_no_offer_section
)
from ..services.generator_service import MessageGeneratorService
from ..services.offers_integration_service import OffersIntegrationService
from .. import cache_utils

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/health", response_model=HealthResponse)
async def health():
    """Endpoint per verificare lo stato del servizio."""
    # Test integrazione offerte
    try:
        offers_service = OffersIntegrationService()
        offers_integration = offers_service.test_connection()
    except Exception:
        offers_integration = False
    
    return {
        "status": "ok",
        "version": "1.0.1",
        "provider": os.getenv("LLM_PROVIDER", "openai"),
        "offers_integration": offers_integration
    }

@router.get("/cache/stats", response_model=CacheStats)
async def cache_stats():
    """Endpoint per verificare statistiche cache."""
    stats = cache_utils.get_cache_stats()
    
    # Aggiungi statistiche specifiche offerte se disponibili
    try:
        offers_service = OffersIntegrationService()
        offers_cached = offers_service.get_cached_offers_count()
        stats["offers_cached"] = offers_cached
    except Exception:
        stats["offers_cached"] = 0
    
    return stats

@router.get("/offers/stats", response_model=OffersStatsResponse)
async def offers_stats():
    """Endpoint per statistiche sulle offerte disponibili."""
    try:
        offers_service = OffersIntegrationService()
        stats = offers_service.get_offers_statistics()
        return stats
    except Exception as e:
        logger.error(f"Errore recupero statistiche offerte: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore recupero statistiche offerte"
        )

@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateRequest,
    llm_client: ChatOpenAI = Depends(get_llm_client)
):
    """
    Genera un messaggio personalizzato con integrazione automatica offerte.
    
    Args:
        req: Richiesta contenente dati utente e POI
        llm_client: Client LLM configurato
        
    Returns:
        GenerateResponse: Messaggio generato con info offerte
    """
    start_time = time.time()
    
    try:
        # Initializza i servizi
        generator_service = MessageGeneratorService(llm_client, get_prompt_template())
        offers_service = OffersIntegrationService()
        
        # Arricchisci POI con offerte se shop_id è presente
        poi_with_offers = None
        if req.poi.shop_id:
            poi_with_offers = offers_service.enrich_poi_with_offers(
                poi=req.poi,
                user_age=req.user.age,
                user_interests=req.user.interests.split(",")
            )
        
        # Genera messaggio (con o senza offerte)
        if poi_with_offers and poi_with_offers.best_offer:
            # Messaggio con offerta
            message, is_cached = generator_service.generate_message_with_offer(
                user_params=req.user.dict(),
                poi_with_offer=poi_with_offers
            )
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            return GenerateResponse(
                message=message,
                cached=is_cached,
                offer_included=True,
                offer_details=poi_with_offers.best_offer,
                personalization_score=_calculate_personalization_score(req.user, poi_with_offers),
                generation_time_ms=generation_time_ms
            )
        else:
            # Messaggio senza offerta (fallback al metodo originale)
            message, is_cached = generator_service.generate_message(
                user_params=req.user.dict(), 
                poi_params=req.poi.dict()
            )
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            return GenerateResponse(
                message=message,
                cached=is_cached,
                offer_included=False,
                personalization_score=_calculate_personalization_score(req.user, None),
                generation_time_ms=generation_time_ms
            )
    
    except Exception as e:
        logger.error(f"Errore nella generazione del messaggio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate/advanced", response_model=GenerateResponse)
async def generate_advanced(
    req: GenerateWithOfferRequest,
    llm_client: ChatOpenAI = Depends(get_llm_client)
):
    """
    Genera un messaggio personalizzato avanzato con controllo completo offerte.
    
    Args:
        req: Richiesta avanzata con POI pre-arricchito di offerte
        llm_client: Client LLM configurato
        
    Returns:
        GenerateResponse: Messaggio generato con controllo avanzato
    """
    start_time = time.time()
    
    try:
        generator_service = MessageGeneratorService(llm_client, get_prompt_template())
        
        # Genera messaggio con controllo livello personalizzazione
        if req.poi.best_offer:
            message, is_cached = generator_service.generate_message_with_offer(
                user_params=req.user.dict(),
                poi_with_offer=req.poi,
                personalization_level=req.personalization_level,
                include_all_offers=req.include_all_offers
            )
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            return GenerateResponse(
                message=message,
                cached=is_cached,
                offer_included=True,
                offer_details=req.poi.best_offer,
                personalization_score=_calculate_personalization_score(req.user, req.poi),
                generation_time_ms=generation_time_ms
            )
        else:
            # Nessuna offerta disponibile
            message, is_cached = generator_service.generate_message(
                user_params=req.user.dict(),
                poi_params=req.poi.dict()
            )
            
            generation_time_ms = (time.time() - start_time) * 1000
            
            return GenerateResponse(
                message=message,
                cached=is_cached,
                offer_included=False,
                personalization_score=_calculate_personalization_score(req.user, None),
                generation_time_ms=generation_time_ms
            )
    
    except Exception as e:
        logger.error(f"Errore nella generazione avanzata del messaggio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/offers/shop/{shop_id}", response_model=List[Offer])
async def get_shop_offers(
    shop_id: int,
    user_age: Optional[int] = Query(None, description="Età utente per filtering"),
    user_interests: Optional[str] = Query(None, description="Interessi utente separati da virgola")
):
    """
    Recupera tutte le offerte attive per un negozio specifico.
    
    Args:
        shop_id: ID del negozio
        user_age: Età utente per filtering (opzionale)
        user_interests: Interessi utente (opzionale)
        
    Returns:
        List[Offer]: Lista offerte disponibili per il negozio
    """
    try:
        offers_service = OffersIntegrationService()
        
        # Converti interessi in lista
        interests_list = []
        if user_interests:
            interests_list = [i.strip() for i in user_interests.split(",")]
        
        offers = offers_service.get_offers_for_shop(
            shop_id=shop_id,
            user_age=user_age,
            user_interests=interests_list
        )
        
        return offers
        
    except Exception as e:
        logger.error(f"Errore recupero offerte per negozio {shop_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore recupero offerte per negozio {shop_id}"
        )

def _calculate_personalization_score(user, poi_with_offers: Optional[POIWithOffer]) -> float:
    """
    Calcola un punteggio di personalizzazione per il messaggio generato.
    
    Args:
        user: Dati utente
        poi_with_offers: POI con offerte (opzionale)
        
    Returns:
        float: Punteggio 0.0-1.0
    """
    score = 0.3  # Base score
    
    # +0.2 se c'è un'offerta
    if poi_with_offers and poi_with_offers.best_offer:
        score += 0.2
        
        # +0.2 se l'offerta è targetizzata
        if poi_with_offers.best_offer.is_targeted:
            score += 0.2
    
    # +0.1 se abbiamo professione specifica
    if user.profession and user.profession.strip():
        score += 0.1
    
    # +0.2 se abbiamo interessi specifici
    if user.interests and len(user.interests.split(",")) > 1:
        score += 0.2
    
    return min(1.0, score)