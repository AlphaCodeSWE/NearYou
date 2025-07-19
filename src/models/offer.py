"""
Modelli dati per le offerte e relativi utility.
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum

class OfferType(Enum):
    """Tipi di offerta disponibili."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_ONE_GET_ONE = "buy_one_get_one"

@dataclass
class Offer:
    """Modello dati per un'offerta."""
    offer_id: Optional[int] = None
    shop_id: int = 0
    discount_percent: int = 0
    description: str = ""
    offer_type: str = OfferType.PERCENTAGE.value
    valid_from: date = None
    valid_until: date = None
    is_active: bool = True
    max_uses: Optional[int] = None
    current_uses: int = 0
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    target_categories: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-inizializzazione per impostare valori di default."""
        if self.valid_from is None:
            self.valid_from = date.today()
        if self.target_categories is None:
            self.target_categories = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte l'offerta in dictionary per inserimento DB."""
        return {
            'shop_id': self.shop_id,
            'discount_percent': self.discount_percent,
            'description': self.description,
            'offer_type': self.offer_type,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until,
            'is_active': self.is_active,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'min_age': self.min_age,
            'max_age': self.max_age,
            'target_categories': self.target_categories
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Offer":
        """Crea un'istanza Offer da dictionary."""
        return cls(
            offer_id=data.get('offer_id'),
            shop_id=data.get('shop_id', 0),
            discount_percent=data.get('discount_percent', 0),
            description=data.get('description', ''),
            offer_type=data.get('offer_type', OfferType.PERCENTAGE.value),
            valid_from=data.get('valid_from'),
            valid_until=data.get('valid_until'),
            is_active=data.get('is_active', True),
            max_uses=data.get('max_uses'),
            current_uses=data.get('current_uses', 0),
            min_age=data.get('min_age'),
            max_age=data.get('max_age'),
            target_categories=data.get('target_categories', []),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def is_valid_for_user(self, user_age: int, user_interests: List[str]) -> bool:
        """Verifica se l'offerta è valida per un utente specifico."""
        # Controllo età
        if self.min_age is not None and user_age < self.min_age:
            return False
        if self.max_age is not None and user_age > self.max_age:
            return False
        
        # Controllo interessi (se specificati)
        if self.target_categories:
            user_interests_lower = [interest.lower().strip() for interest in user_interests]
            target_lower = [cat.lower().strip() for cat in self.target_categories]
            if not any(interest in target_lower for interest in user_interests_lower):
                return False
        
        # Controllo date
        today = date.today()
        if today < self.valid_from or today > self.valid_until:
            return False
        
        # Controllo usi massimi
        if self.max_uses is not None and self.current_uses >= self.max_uses:
            return False
        
        return self.is_active
    
    def get_display_text(self, shop_name: str = "") -> str:
        """Genera testo descrittivo per l'offerta."""
        if self.offer_type == OfferType.PERCENTAGE.value:
            if shop_name:
                return f"Sconto del {self.discount_percent}% da {shop_name}!"
            return f"Sconto del {self.discount_percent}%!"
        elif self.offer_type == OfferType.BUY_ONE_GET_ONE.value:
            return f"Compra 1 e prendi 2 da {shop_name}!" if shop_name else "Compra 1 e prendi 2!"
        else:
            return self.description or f"Offerta speciale da {shop_name}!" if shop_name else "Offerta speciale!"

@dataclass 
class UserVisit:
    """Modello dati per una visita utente presso un negozio."""
    visit_id: Optional[int] = None
    user_id: int = 0
    shop_id: int = 0
    offer_id: int = 0
    visit_start_time: Optional[datetime] = None
    visit_end_time: Optional[datetime] = None
    duration_minutes: int = 0
    offer_accepted: bool = False
    estimated_spending: float = 0.0
    user_satisfaction: int = 5  # 1-10
    day_of_week: Optional[int] = None
    hour_of_day: Optional[int] = None
    weather_condition: str = ""
    user_age: int = 0
    user_profession: str = ""
    user_interests: str = ""
    shop_name: str = ""
    shop_category: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-inizializzazione per calcolare campi derivati."""
        if self.visit_start_time:
            self.day_of_week = self.visit_start_time.weekday() + 1  # 1=Monday
            self.hour_of_day = self.visit_start_time.hour
            
        if self.visit_start_time and self.visit_end_time:
            delta = self.visit_end_time - self.visit_start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte la visita in dictionary per inserimento DB."""
        return {
            'visit_id': self.visit_id or 0,
            'user_id': self.user_id,
            'shop_id': self.shop_id,
            'offer_id': self.offer_id,
            'visit_start_time': self.visit_start_time,
            'visit_end_time': self.visit_end_time,
            'duration_minutes': self.duration_minutes,
            'offer_accepted': self.offer_accepted,
            'estimated_spending': self.estimated_spending,
            'user_satisfaction': self.user_satisfaction,
            'day_of_week': self.day_of_week or 0,
            'hour_of_day': self.hour_of_day or 0,
            'weather_condition': self.weather_condition,
            'user_age': self.user_age,
            'user_profession': self.user_profession,
            'user_interests': self.user_interests,
            'shop_name': self.shop_name,
            'shop_category': self.shop_category,
            'created_at': self.created_at
        }