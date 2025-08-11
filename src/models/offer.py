"""
Modelli dati per le offerte e relativi utility con Builder Pattern.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Protocol
from enum import Enum
from abc import ABC, abstractmethod

class OfferType(Enum):
    """Tipi di offerta disponibili."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_ONE_GET_ONE = "buy_one_get_one"

class OfferValidatorProtocol(Protocol):
    """Protocol for offer validation."""
    
    def validate(self, offer: 'Offer') -> bool:
        """Validate an offer."""
        ...

class OfferValidator:
    """Default offer validator implementation."""
    
    def validate(self, offer: 'Offer') -> bool:
        """Validate offer basic constraints."""
        if offer.discount_percent < 0 or offer.discount_percent > 100:
            return False
        if offer.valid_from and offer.valid_until and offer.valid_from > offer.valid_until:
            return False
        if offer.min_age and offer.max_age and offer.min_age > offer.max_age:
            return False
        return True

@dataclass
class Offer:
    """Modello dati per un'offerta con validazione integrata."""
    offer_id: Optional[int] = None
    shop_id: int = 0
    discount_percent: int = 0
    description: str = ""
    offer_type: str = OfferType.PERCENTAGE.value
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: bool = True
    max_uses: Optional[int] = None
    current_uses: int = 0
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    target_categories: Optional[List[str]] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    _validator: OfferValidatorProtocol = field(default_factory=OfferValidator, init=False)
    
    def __post_init__(self):
        """Post-inizializzazione per impostare valori di default."""
        if self.valid_from is None:
            self.valid_from = date.today()
        if self.target_categories is None:
            self.target_categories = []
    
    def set_validator(self, validator: OfferValidatorProtocol) -> None:
        """Set custom validator (Strategy pattern for validation)."""
        self._validator = validator
    
    def is_valid(self) -> bool:
        """Check if offer is valid using current validator."""
        return self._validator.validate(self)
    
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
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
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

class OfferBuilder:
    """
    Builder pattern implementation for creating Offer objects.
    Provides a fluent interface for constructing complex offers.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self) -> 'OfferBuilder':
        """Reset builder to initial state."""
        self._offer = Offer()
        return self
    
    def shop(self, shop_id: int) -> 'OfferBuilder':
        """Set shop ID."""
        self._offer.shop_id = shop_id
        return self
    
    def discount(self, percentage: int) -> 'OfferBuilder':
        """Set discount percentage."""
        self._offer.discount_percent = percentage
        return self
    
    def description(self, text: str) -> 'OfferBuilder':
        """Set offer description."""
        self._offer.description = text
        return self
    
    def offer_type(self, offer_type: OfferType) -> 'OfferBuilder':
        """Set offer type."""
        self._offer.offer_type = offer_type.value
        return self
    
    def valid_period(self, from_date: date, until_date: date) -> 'OfferBuilder':
        """Set validity period."""
        self._offer.valid_from = from_date
        self._offer.valid_until = until_date
        return self
    
    def valid_for_days(self, days: int) -> 'OfferBuilder':
        """Set validity for a number of days from today."""
        from datetime import timedelta
        self._offer.valid_from = date.today()
        self._offer.valid_until = date.today() + timedelta(days=days)
        return self
    
    def max_uses(self, uses: int) -> 'OfferBuilder':
        """Set maximum number of uses."""
        self._offer.max_uses = uses
        return self
    
    def age_target(self, min_age: Optional[int] = None, max_age: Optional[int] = None) -> 'OfferBuilder':
        """Set age targeting."""
        self._offer.min_age = min_age
        self._offer.max_age = max_age
        return self
    
    def interest_target(self, categories: List[str]) -> 'OfferBuilder':
        """Set interest targeting."""
        self._offer.target_categories = categories.copy()
        return self
    
    def active(self, is_active: bool = True) -> 'OfferBuilder':
        """Set active status."""
        self._offer.is_active = is_active
        return self
    
    def build(self) -> Offer:
        """Build and return the final Offer object."""
        if not self._offer.is_valid():
            raise ValueError("Cannot build invalid offer. Check constraints.")
        
        result = self._offer
        self.reset()  # Reset for next use
        return result
    
    def build_unsafe(self) -> Offer:
        """Build without validation (for special cases)."""
        result = self._offer
        self.reset()
        return result

class OfferFactory:
    """Factory for creating common offer types."""
    
    @staticmethod
    def create_flash_offer(shop_id: int, shop_name: str, discount: int, hours: int = 24) -> Offer:
        """Create a flash offer with short duration."""
        return (OfferBuilder()
                .shop(shop_id)
                .discount(discount)
                .description(f"🔥 OFFERTA FLASH: {discount}% di sconto da {shop_name}!")
                .valid_for_days(max(1, hours // 24))
                .max_uses(50)
                .build())
    
    @staticmethod
    def create_student_offer(shop_id: int, shop_name: str, discount: int = 15) -> Offer:
        """Create a student-targeted offer."""
        return (OfferBuilder()
                .shop(shop_id)
                .discount(discount)
                .description(f"📚 Sconto studenti: {discount}% da {shop_name}!")
                .age_target(min_age=16, max_age=30)
                .interest_target(["studio", "libri", "università"])
                .valid_for_days(30)
                .max_uses(100)
                .build())
    
    @staticmethod
    def create_senior_offer(shop_id: int, shop_name: str, discount: int = 20) -> Offer:
        """Create a senior-targeted offer."""
        return (OfferBuilder()
                .shop(shop_id)
                .discount(discount)
                .description(f"👴 Sconto senior: {discount}% da {shop_name}!")
                .age_target(min_age=65)
                .valid_for_days(60)
                .max_uses(200)
                .build())
    
    @staticmethod
    def create_category_offer(shop_id: int, shop_name: str, category: str, discount: int = 25) -> Offer:
        """Create a category-specific offer."""
        category_interests = {
            "ristorante": ["cucina", "cibo", "gastronomia"],
            "bar": ["caffè", "aperitivo", "socializing"],
            "abbigliamento": ["moda", "style", "shopping"],
            "palestra": ["fitness", "sport", "allenamento"]
        }
        
        interests = category_interests.get(category.lower(), [category])
        
        return (OfferBuilder()
                .shop(shop_id)
                .discount(discount)
                .description(f"🎯 Offerta {category}: {discount}% da {shop_name}!")
                .interest_target(interests)
                .valid_for_days(21)
                .max_uses(150)
                .build())

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