"""
Servizio principale per la generazione di messaggi personalizzati con offerte.
"""
import logging
import hashlib
from typing import Dict, Any, Tuple, Optional

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from ..api.models import POIWithOffer, Offer
from ..api.dependencies import get_offer_section_template, get_no_offer_section
from .. import cache_utils

logger = logging.getLogger(__name__)

class MessageGeneratorService:
    """Servizio per generazione messaggi personalizzati con supporto offerte."""
    
    def __init__(self, llm_client: ChatOpenAI, prompt_template: str):
        """
        Inizializza il servizio.
        
        Args:
            llm_client: Client LLM configurato
            prompt_template: Template per il prompt
        """
        self.llm_client = llm_client
        self.prompt_template = prompt_template
    
    def generate_message(
        self, 
        user_params: Dict[str, Any], 
        poi_params: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Genera messaggio personalizzato (metodo originale senza offerte).
        
        Args:
            user_params: Parametri utente
            poi_params: Parametri POI
            
        Returns:
            Tuple[str, bool]: (messaggio, is_cached)
        """
        # Crea chiave cache
        cache_key = self._create_cache_key(user_params, poi_params)
        
        # Controlla cache
        cached_message = cache_utils.get_cached_message(cache_key)
        if cached_message:
            logger.debug(f"Messaggio recuperato dalla cache per chiave: {cache_key}")
            return cached_message, True
        
        # Genera nuovo messaggio
        try:
            # Usa sezione "nessuna offerta"
            offer_section = get_no_offer_section()
            
            prompt = self.prompt_template.format(
                age=user_params.get('age', 'N/A'),
                profession=user_params.get('profession', 'N/A'),
                interests=user_params.get('interests', 'N/A'),
                name=poi_params.get('name', 'N/A'),
                category=poi_params.get('category', 'N/A'),
                description=poi_params.get('description', 'N/A'),
                offer_section=offer_section
            )
            
            response = self.llm_client([HumanMessage(content=prompt)])
            message = response.content.strip()
            
            # Salva in cache
            cache_utils.cache_message(cache_key, message)
            
            logger.info(f"Messaggio generato e cachato per chiave: {cache_key}")
            return message, False
            
        except Exception as e:
            logger.error(f"Errore generazione messaggio: {e}")
            # Fallback
            return f"Scopri {poi_params.get('name', 'questo posto')} a pochi passi da te!", False
    
    def generate_message_with_offer(
        self,
        user_params: Dict[str, Any],
        poi_with_offer: POIWithOffer,
        personalization_level: str = "standard",
        include_all_offers: bool = False
    ) -> Tuple[str, bool]:
        """
        Genera messaggio personalizzato che include offerte.
        
        Args:
            user_params: Parametri utente
            poi_with_offer: POI arricchito con offerte
            personalization_level: Livello personalizzazione
            include_all_offers: Se includere tutte le offerte
            
        Returns:
            Tuple[str, bool]: (messaggio, is_cached)
        """
        # Crea chiave cache che include l'offerta
        cache_key = self._create_cache_key_with_offer(user_params, poi_with_offer)
        
        # Controlla cache
        cached_message = cache_utils.get_cached_message(cache_key)
        if cached_message:
            logger.debug(f"Messaggio con offerta recuperato dalla cache: {cache_key}")
            return cached_message, True
        
        try:
            # Prepara sezione offerta
            if poi_with_offer.best_offer:
                offer_section = self._format_offer_section(poi_with_offer.best_offer)
            else:
                offer_section = get_no_offer_section()
            
            # Genera prompt con offerta
            prompt = self._create_prompt_with_offer(
                user_params, poi_with_offer, offer_section, personalization_level
            )
            
            # Genera messaggio
            response = self.llm_client([HumanMessage(content=prompt)])
            message = response.content.strip()
            
            # Post-processing per personalizzazione avanzata
            if personalization_level == "advanced":
                message = self._enhance_message_advanced(message, user_params, poi_with_offer)
            
            # Salva in cache
            cache_utils.cache_message(cache_key, message)
            
            logger.info(f"Messaggio con offerta generato: {poi_with_offer.name}, sconto: {poi_with_offer.best_offer.discount_percent if poi_with_offer.best_offer else 0}%")
            return message, False
            
        except Exception as e:
            logger.error(f"Errore generazione messaggio con offerta: {e}")
            # Fallback al messaggio base
            poi_params = {
                'name': poi_with_offer.name,
                'category': poi_with_offer.category,
                'description': poi_with_offer.description
            }
            return self.generate_message(user_params, poi_params)
    
    def _format_offer_section(self, offer: Offer) -> str:
        """
        Formatta la sezione offerta per il prompt.
        
        Args:
            offer: Offerta da formattare
            
        Returns:
            str: Sezione offerta formattata
        """
        template = get_offer_section_template()
        
        # Calcola utilizzi rimasti
        remaining_uses = "Illimitati"
        if offer.max_uses:
            remaining = offer.max_uses - offer.current_uses
            remaining_uses = f"{remaining} utilizzi" if remaining > 0 else "Quasi esaurita!"
        
        return template.format(
            discount_percent=offer.discount_percent,
            offer_description=offer.description,
            valid_until=offer.valid_until,
            remaining_uses=remaining_uses
        )
    
    def _create_prompt_with_offer(
        self,
        user_params: Dict[str, Any],
        poi_with_offer: POIWithOffer,
        offer_section: str,
        personalization_level: str
    ) -> str:
        """
        Crea prompt completo includendo offerta e livello personalizzazione.
        
        Args:
            user_params: Parametri utente
            poi_with_offer: POI con offerte
            offer_section: Sezione offerta formattata
            personalization_level: Livello personalizzazione
            
        Returns:
            str: Prompt completo
        """
        base_prompt = self.prompt_template.format(
            age=user_params.get('age', 'N/A'),
            profession=user_params.get('profession', 'N/A'),
            interests=user_params.get('interests', 'N/A'),
            name=poi_with_offer.name,
            category=poi_with_offer.category,
            description=poi_with_offer.description,
            offer_section=offer_section
        )
        
        # Aggiungi istruzioni specifiche per livello personalizzazione
        if personalization_level == "advanced":
            base_prompt += "\n\nIstruzioni avanzate:\n"
            base_prompt += "- Usa un linguaggio molto personalizzato basato su età e professione\n"
            base_prompt += "- Includi dettagli specifici sull'offerta che creano urgenza\n"
            base_prompt += "- Connetti l'offerta agli interessi dell'utente in modo naturale\n"
        elif personalization_level == "basic":
            base_prompt += "\n\nIstruzioni base:\n"
            base_prompt += "- Mantieni il messaggio semplice e diretto\n"
            base_prompt += "- Menziona l'offerta in modo chiaro\n"
        
        return base_prompt
    
    def _enhance_message_advanced(
        self,
        message: str,
        user_params: Dict[str, Any],
        poi_with_offer: POIWithOffer
    ) -> str:
        """
        Migliora il messaggio per personalizzazione avanzata.
        
        Args:
            message: Messaggio base
            user_params: Parametri utente
            poi_with_offer: POI con offerte
            
        Returns:
            str: Messaggio migliorato
        """
        # Post-processing personalizzato (opzionale)
        # Per ora restituisci il messaggio originale
        return message
    
    def _create_cache_key(self, user_params: Dict[str, Any], poi_params: Dict[str, Any]) -> str:
        """
        Crea chiave cache per messaggio senza offerte.
        
        Args:
            user_params: Parametri utente
            poi_params: Parametri POI
            
        Returns:
            str: Chiave cache
        """
        # Combina parametri rilevanti per cache
        cache_data = {
            'age': user_params.get('age'),
            'profession': user_params.get('profession', '').lower(),
            'interests': user_params.get('interests', '').lower(),
            'poi_name': poi_params.get('name', '').lower(),
            'poi_category': poi_params.get('category', '').lower()
        }
        
        # Crea hash
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _create_cache_key_with_offer(
        self, 
        user_params: Dict[str, Any], 
        poi_with_offer: POIWithOffer
    ) -> str:
        """
        Crea chiave cache per messaggio con offerte.
        
        Args:
            user_params: Parametri utente
            poi_with_offer: POI con offerte
            
        Returns:
            str: Chiave cache
        """
        # Include anche dati offerta nella cache key
        cache_data = {
            'age': user_params.get('age'),
            'profession': user_params.get('profession', '').lower(),
            'interests': user_params.get('interests', '').lower(),
            'poi_name': poi_with_offer.name.lower(),
            'poi_category': poi_with_offer.category.lower(),
            'offer_id': poi_with_offer.best_offer.offer_id if poi_with_offer.best_offer else None,
            'discount': poi_with_offer.best_offer.discount_percent if poi_with_offer.best_offer else None
        }
        
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode()).hexdigest()