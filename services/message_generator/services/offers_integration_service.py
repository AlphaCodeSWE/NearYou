"""
Servizio per l'integrazione delle offerte nel message generator.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import psycopg2
from psycopg2.extras import RealDictCursor

from ..api.models import POI, POIWithOffer, Offer
from ..api.dependencies import get_postgres_connection

logger = logging.getLogger(__name__)

class OffersIntegrationService:
    """Servizio per integrare le offerte nei messaggi."""
    
    def __init__(self):
        """Inizializza il servizio."""
        self._connection_cache = None
    
    def get_connection(self):
        """Ottiene connessione PostgreSQL con caching."""
        if self._connection_cache is None or self._connection_cache.closed:
            self._connection_cache = get_postgres_connection()
        return self._connection_cache
    
    def test_connection(self) -> bool:
        """Testa la connessione al database delle offerte."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM offers WHERE is_active = true")
                    result = cur.fetchone()
                    return result[0] >= 0
        except Exception as e:
            logger.error(f"Test connessione offerte fallito: {e}")
            return False
    
    def enrich_poi_with_offers(
        self, 
        poi: POI, 
        user_age: Optional[int] = None,
        user_interests: Optional[List[str]] = None
    ) -> POIWithOffer:
        """
        Arricchisce un POI con le migliori offerte disponibili.
        
        Args:
            poi: Point of Interest base
            user_age: Età utente per targeting
            user_interests: Lista interessi utente
            
        Returns:
            POIWithOffer: POI arricchito con offerte
        """
        if not poi.shop_id:
            # Nessun shop_id, restituisci POI senza offerte
            return POIWithOffer(
                name=poi.name,
                category=poi.category,
                description=poi.description,
                shop_id=poi.shop_id,
                best_offer=None,
                offers_count=0
            )
        
        try:
            # Recupera tutte le offerte per il negozio
            offers = self.get_offers_for_shop(
                shop_id=poi.shop_id,
                user_age=user_age,
                user_interests=user_interests or []
            )
            
            # Trova la migliore offerta
            best_offer = self._select_best_offer(offers, user_age, user_interests or [])
            
            return POIWithOffer(
                name=poi.name,
                category=poi.category,
                description=poi.description,
                shop_id=poi.shop_id,
                best_offer=best_offer,
                offers_count=len(offers)
            )
            
        except Exception as e:
            logger.error(f"Errore arricchimento POI {poi.shop_id} con offerte: {e}")
            # Fallback: restituisci POI senza offerte
            return POIWithOffer(
                name=poi.name,
                category=poi.category,
                description=poi.description,
                shop_id=poi.shop_id,
                best_offer=None,
                offers_count=0
            )
    
    def get_offers_for_shop(
        self,
        shop_id: int,
        user_age: Optional[int] = None,
        user_interests: Optional[List[str]] = None
    ) -> List[Offer]:
        """
        Recupera tutte le offerte attive per un negozio.
        
        Args:
            shop_id: ID del negozio
            user_age: Età utente per filtering
            user_interests: Lista interessi utente
            
        Returns:
            List[Offer]: Lista offerte filtrate e validate
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Query base per offerte attive
                    query = """
                        SELECT 
                            offer_id, discount_percent, description, 
                            valid_until, max_uses, current_uses,
                            min_age, max_age, target_categories
                        FROM offers 
                        WHERE shop_id = %s 
                          AND is_active = true 
                          AND valid_from <= CURRENT_DATE 
                          AND valid_until >= CURRENT_DATE
                          AND (max_uses IS NULL OR current_uses < max_uses)
                        ORDER BY discount_percent DESC, valid_until ASC
                    """
                    
                    cur.execute(query, (shop_id,))
                    rows = cur.fetchall()
                    
                    offers = []
                    for row in rows:
                        # Controlla se l'offerta è valida per l'utente
                        is_targeted = self._is_offer_targeted_for_user(
                            row, user_age, user_interests
                        )
                        
                        # Se l'offerta ha targeting specifico, mostra solo se match
                        if self._has_targeting(row) and not is_targeted:
                            continue
                        
                        offer = Offer(
                            offer_id=row['offer_id'],
                            discount_percent=row['discount_percent'],
                            description=row['description'],
                            valid_until=row['valid_until'].strftime('%Y-%m-%d'),
                            max_uses=row['max_uses'],
                            current_uses=row['current_uses'],
                            is_targeted=is_targeted
                        )
                        offers.append(offer)
                    
                    return offers
                    
        except Exception as e:
            logger.error(f"Errore recupero offerte per negozio {shop_id}: {e}")
            return []
    
    def get_offers_statistics(self) -> Dict[str, Any]:
        """
        Recupera statistiche generali sulle offerte.
        
        Returns:
            Dict: Statistiche complete offerte
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Conta totale offerte attive
                    cur.execute("""
                        SELECT COUNT(*) as total_active_offers
                        FROM offers 
                        WHERE is_active = true 
                          AND valid_until >= CURRENT_DATE
                    """)
                    total_active = cur.fetchone()['total_active_offers']
                    
                    # Offerte per categoria
                    cur.execute("""
                        SELECT s.category, COUNT(o.offer_id) as count
                        FROM shops s
                        JOIN offers o ON s.shop_id = o.shop_id
                        WHERE o.is_active = true 
                          AND o.valid_until >= CURRENT_DATE
                        GROUP BY s.category
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    by_category = {row['category']: row['count'] for row in cur.fetchall()}
                    
                    # Sconto medio
                    cur.execute("""
                        SELECT AVG(discount_percent) as avg_discount
                        FROM offers 
                        WHERE is_active = true 
                          AND valid_until >= CURRENT_DATE
                    """)
                    avg_discount = cur.fetchone()['avg_discount'] or 0.0
                    
                    # Top 5 sconti
                    cur.execute("""
                        SELECT s.shop_name, o.discount_percent, o.description
                        FROM offers o
                        JOIN shops s ON o.shop_id = s.shop_id
                        WHERE o.is_active = true 
                          AND o.valid_until >= CURRENT_DATE
                        ORDER BY o.discount_percent DESC
                        LIMIT 5
                    """)
                    top_discounts = [
                        {
                            'shop_name': row['shop_name'],
                            'discount': row['discount_percent'],
                            'description': row['description']
                        }
                        for row in cur.fetchall()
                    ]
                    
                    # Offerte in scadenza
                    cur.execute("""
                        SELECT COUNT(*) as expiring_soon
                        FROM offers 
                        WHERE is_active = true 
                          AND valid_until >= CURRENT_DATE
                          AND valid_until <= CURRENT_DATE + INTERVAL '7 days'
                    """)
                    expiring_soon = cur.fetchone()['expiring_soon']
                    
                    return {
                        'total_active_offers': total_active,
                        'offers_by_category': by_category,
                        'avg_discount_percent': round(avg_discount, 1),
                        'top_discounts': top_discounts,
                        'expiring_soon': expiring_soon
                    }
                    
        except Exception as e:
            logger.error(f"Errore recupero statistiche offerte: {e}")
            return {
                'total_active_offers': 0,
                'offers_by_category': {},
                'avg_discount_percent': 0.0,
                'top_discounts': [],
                'expiring_soon': 0
            }
    
    def get_cached_offers_count(self) -> int:
        """
        Restituisce il numero di offerte attualmente in cache.
        
        Returns:
            int: Numero offerte in cache
        """
        # Placeholder - implementazione dipende dal sistema di cache
        # Per ora restituisci un valore fisso
        return 0
    
    def _select_best_offer(
        self, 
        offers: List[Offer], 
        user_age: Optional[int],
        user_interests: List[str]
    ) -> Optional[Offer]:
        """
        Seleziona la migliore offerta per l'utente.
        
        Args:
            offers: Lista offerte disponibili
            user_age: Età utente
            user_interests: Interessi utente
            
        Returns:
            Optional[Offer]: Migliore offerta o None
        """
        if not offers:
            return None
        
        # Priorità:
        # 1. Offerte targetizzate per l'utente
        # 2. Sconto più alto
        # 3. Scadenza più vicina (urgenza)
        
        targeted_offers = [o for o in offers if o.is_targeted]
        if targeted_offers:
            # Prendi la migliore tra quelle targetizzate
            return max(targeted_offers, key=lambda x: x.discount_percent)
        
        # Altrimenti prendi quella con sconto più alto
        return max(offers, key=lambda x: x.discount_percent)
    
    def _is_offer_targeted_for_user(
        self, 
        offer_row: Dict, 
        user_age: Optional[int],
        user_interests: Optional[List[str]]
    ) -> bool:
        """
        Verifica se un'offerta è targetizzata per l'utente specifico.
        
        Args:
            offer_row: Riga database dell'offerta
            user_age: Età utente
            user_interests: Interessi utente
            
        Returns:
            bool: True se l'offerta è targetizzata per l'utente
        """
        # Controllo età
        if user_age is not None:
            if offer_row.get('min_age') and user_age < offer_row['min_age']:
                return False
            if offer_row.get('max_age') and user_age > offer_row['max_age']:
                return False
        
        # Controllo interessi
        target_categories = offer_row.get('target_categories')
        if target_categories and user_interests:
            user_interests_lower = [i.lower().strip() for i in user_interests]
            target_lower = [cat.lower().strip() for cat in target_categories]
            
            # Se c'è almeno un match negli interessi
            if any(interest in target_lower for interest in user_interests_lower):
                return True
            
            # Se non c'è match negli interessi ma c'è targeting, non è per questo utente
            return False
        
        # Se non c'è targeting specifico, è valida per tutti
        return not self._has_targeting(offer_row)
    
    def _has_targeting(self, offer_row: Dict) -> bool:
        """
        Verifica se un'offerta ha targeting specifico.
        
        Args:
            offer_row: Riga database dell'offerta
            
        Returns:
            bool: True se ha targeting specifico
        """
        return (
            offer_row.get('min_age') is not None or
            offer_row.get('max_age') is not None or
            (offer_row.get('target_categories') and len(offer_row['target_categories']) > 0)
        )