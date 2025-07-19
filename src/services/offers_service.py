"""
Servizio per la gestione delle offerte.
"""
import random
import logging
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from src.models.offer import Offer, OfferType
from src.config.offers_config import (
    CATEGORY_DISCOUNT_RANGES, CATEGORY_OFFER_DURATION,
    CATEGORY_DESCRIPTIONS, INTEREST_TARGETING,
    CATEGORY_OFFER_PROBABILITY, CATEGORY_MAX_USES,
    CATEGORY_AGE_TARGETING, MIN_OFFERS_PER_SHOP, MAX_OFFERS_PER_SHOP,
    DEFAULT_DISCOUNT_RANGE, DEFAULT_DURATION_RANGE, DEFAULT_MAX_USES_RANGE
)

logger = logging.getLogger(__name__)

class OffersService:
    """Servizio per la gestione delle offerte nei negozi."""
    
    def __init__(self, postgres_config: Dict[str, Any]):
        """
        Inizializza il servizio con la configurazione PostgreSQL.
        
        Args:
            postgres_config: Configurazione connessione PostgreSQL
        """
        self.postgres_config = postgres_config
        
    def get_connection(self):
        """Ottiene connessione PostgreSQL."""
        return psycopg2.connect(
            host=self.postgres_config['host'],
            port=self.postgres_config['port'],
            user=self.postgres_config['user'],
            password=self.postgres_config['password'],
            database=self.postgres_config['database']
        )
    
    def generate_offers_for_all_shops(self) -> int:
        """
        Genera offerte per tutti i negozi nel database.
        
        Returns:
            int: Numero di offerte generate
        """
        total_offers = 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Recupera tutti i negozi
                    cur.execute("SELECT shop_id, shop_name, category FROM shops WHERE category IS NOT NULL")
                    shops = cur.fetchall()
                    
                    logger.info(f"Trovati {len(shops)} negozi per generare offerte")
                    
                    for shop in shops:
                        shop_offers = self.generate_offers_for_shop(
                            shop_id=shop['shop_id'],
                            shop_name=shop['shop_name'],
                            category=shop['category']
                        )
                        
                        if shop_offers:
                            inserted = self.insert_offers(shop_offers)
                            total_offers += inserted
                            logger.info(f"Generate {inserted} offerte per {shop['shop_name']} ({shop['category']})")
        
        except Exception as e:
            logger.error(f"Errore nella generazione delle offerte: {e}")
            raise
        
        return total_offers
    
    def generate_offers_for_shop(self, shop_id: int, shop_name: str, category: str) -> List[Offer]:
        """
        Genera offerte casuali per un singolo negozio.
        
        Args:
            shop_id: ID del negozio
            shop_name: Nome del negozio
            category: Categoria del negozio
            
        Returns:
            List[Offer]: Lista delle offerte generate
        """
        # Verifica se generare offerte per questa categoria
        probability = CATEGORY_OFFER_PROBABILITY.get(category.lower(), 0.5)
        if random.random() > probability:
            logger.debug(f"Saltata generazione offerte per {shop_name} (probabilità: {probability})")
            return []
        
        # Numero casuale di offerte da generare
        num_offers = random.randint(MIN_OFFERS_PER_SHOP, MAX_OFFERS_PER_SHOP)
        offers = []
        
        for i in range(num_offers):
            offer = self._create_random_offer(shop_id, shop_name, category)
            if offer:
                offers.append(offer)
        
        return offers
    
    def _create_random_offer(self, shop_id: int, shop_name: str, category: str) -> Optional[Offer]:
        """
        Crea una singola offerta casuale per un negozio.
        
        Args:
            shop_id: ID del negozio
            shop_name: Nome del negozio  
            category: Categoria del negozio
            
        Returns:
            Optional[Offer]: Offerta generata o None
        """
        try:
            # Sconto casuale basato sulla categoria
            discount_range = CATEGORY_DISCOUNT_RANGES.get(
                category.lower(), DEFAULT_DISCOUNT_RANGE
            )
            discount = random.randint(discount_range[0], discount_range[1])
            
            # Durata casuale basata sulla categoria
            duration_range = CATEGORY_OFFER_DURATION.get(
                category.lower(), DEFAULT_DURATION_RANGE
            )
            duration_days = random.randint(duration_range[0], duration_range[1])
            
            # Date validità
            valid_from = date.today()
            valid_until = valid_from + timedelta(days=duration_days)
            
            # Descrizione casuale
            descriptions = CATEGORY_DESCRIPTIONS.get(category.lower(), [
                f"Offerta speciale da {shop_name}!",
                f"Sconto esclusivo del {discount}%!",
                f"Promozione limitata da {shop_name}!"
            ])
            description = random.choice(descriptions)
            if "{discount}" in description:
                description = description.replace("{discount}", str(discount))
            
            # Usi massimi
            max_uses_range = CATEGORY_MAX_USES.get(
                category.lower(), DEFAULT_MAX_USES_RANGE
            )
            max_uses = random.randint(max_uses_range[0], max_uses_range[1])
            
            # Targeting età (casuale)
            age_targeting = CATEGORY_AGE_TARGETING.get(category.lower(), {})
            min_age, max_age = None, None
            if age_targeting and random.random() < 0.3:  # 30% probabilità di age targeting
                target_group = random.choice(list(age_targeting.keys()))
                min_age, max_age = age_targeting[target_group]
            
            # Targeting interessi
            target_categories = None
            interests = INTEREST_TARGETING.get(category.lower(), [])
            if interests and random.random() < 0.4:  # 40% probabilità di interest targeting
                target_categories = random.sample(interests, min(2, len(interests)))
            
            return Offer(
                shop_id=shop_id,
                discount_percent=discount,
                description=description,
                offer_type=OfferType.PERCENTAGE.value,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=True,
                max_uses=max_uses,
                current_uses=0,
                min_age=min_age,
                max_age=max_age,
                target_categories=target_categories
            )
            
        except Exception as e:
            logger.error(f"Errore creazione offerta per negozio {shop_id}: {e}")
            return None
    
    def insert_offers(self, offers: List[Offer]) -> int:
        """
        Inserisce le offerte nel database.
        
        Args:
            offers: Lista delle offerte da inserire
            
        Returns:
            int: Numero di offerte inserite con successo
        """
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
                                )
                            """, offer.to_dict())
                            inserted_count += 1
                            
                        except Exception as e:
                            logger.error(f"Errore inserimento singola offerta: {e}")
                            continue
                    
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Errore inserimento offerte: {e}")
            raise
        
        return inserted_count
    
    def get_active_offers_for_shop(self, shop_id: int) -> List[Dict[str, Any]]:
        """
        Recupera le offerte attive per un negozio.
        
        Args:
            shop_id: ID del negozio
            
        Returns:
            List[Dict]: Lista delle offerte attive
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM offers 
                        WHERE shop_id = %s 
                          AND is_active = true 
                          AND valid_from <= CURRENT_DATE 
                          AND valid_until >= CURRENT_DATE
                          AND (max_uses IS NULL OR current_uses < max_uses)
                        ORDER BY discount_percent DESC
                    """, (shop_id,))
                    
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            logger.error(f"Errore recupero offerte per negozio {shop_id}: {e}")
            return []
    
    def cleanup_expired_offers(self) -> int:
        """
        Disattiva le offerte scadute.
        
        Returns:
            int: Numero di offerte disattivate
        """
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
                    
                    logger.info(f"Disattivate {updated_count} offerte scadute")
                    return updated_count
                    
        except Exception as e:
            logger.error(f"Errore cleanup offerte scadute: {e}")
            return 0