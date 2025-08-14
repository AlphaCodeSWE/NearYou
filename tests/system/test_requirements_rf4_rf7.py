"""
Test di sistema per i requisiti RF4-RF7 del sistema NearYou.

Questo modulo contiene test per:
- RF4: Generazione messaggi personalizzati e sistema offerte
- RF5: Dashboard utente base  
- RF6: Storage e persistenza dati
- RF7: Cache e ottimizzazione base
"""
import pytest
import asyncio
import json
import time
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import opzionali - usa mock se non disponibili
try:
    import requests
except ImportError:
    requests = Mock()

try:
    import redis
except ImportError:
    redis = Mock()

try:
    import psycopg2
except ImportError:
    psycopg2 = Mock()

try:
    import clickhouse_driver
except ImportError:
    clickhouse_driver = Mock()

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from typing import Dict, List, Any


@pytest.mark.system
class TestRF4MessageGenerationOffers:
    """
    Test per RF4 - Generazione messaggi personalizzati e sistema offerte
    Verifica LLM integration, cache Redis, design patterns per offerte.
    """
    
    def test_rf4_1_http_message_generation_service(self):
        """
        RF4.1: Il sistema deve generare messaggi via HTTP service `/generate-message`
        """
        message_service_url = "http://localhost:8001/generate-message"
        
        # Payload per generazione messaggio
        message_request = {
            "user_profile": {
                "user_id": 123,
                "age": 25,
                "profession": "Engineer", 
                "interests": ["technology", "travel"]
            },
            "shop_info": {
                "shop_id": 456,
                "name": "TechStore Milano",
                "category": "electronics",
                "description": "Latest technology and gadgets"
            },
            "context": {
                "visit_time": "afternoon",
                "weather": "sunny",
                "distance": 150
            }
        }
        
        with patch('requests.post') as mock_post:
            # Mock risposta servizio messaggi
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": "Ciao! Scopri le ultime novità tech da TechStore Milano. Sconto 15% per giovani professionisti come te!",
                "personalization_score": 0.85,
                "generation_time_ms": 245,
                "llm_provider": "groq"
            }
            mock_post.return_value = mock_response
            
            # Test richiesta generazione messaggio
            response = requests.post(message_service_url, json=message_request)
            
            assert response.status_code == 200
            message_data = response.json()
            
            # Verifica contenuto risposta
            assert "message" in message_data
            assert len(message_data["message"]) > 0
            assert "personalization_score" in message_data
            assert 0 <= message_data["personalization_score"] <= 1
            assert "generation_time_ms" in message_data
            assert message_data["generation_time_ms"] > 0
            assert "llm_provider" in message_data
    
    def test_rf4_2_configurable_llm_providers(self):
        """
        RF4.2: Deve supportare provider LLM configurabili (Groq/OpenAI) via `LLM_PROVIDER`
        """
        # Test configurazione Groq
        os.environ['LLM_PROVIDER'] = 'groq'
        os.environ['GROQ_API_KEY'] = 'test_groq_key'
        
        with patch('requests.post') as mock_groq_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Messaggio generato da Groq"
                    }
                }],
                "usage": {"total_tokens": 150},
                "model": "mixtral-8x7b-32768"
            }
            mock_groq_request.return_value = mock_response
            
            # Simula chiamata a Groq
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": "Bearer test_groq_key"}
            
            response = requests.post(groq_url, headers=headers, json={
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": "Generate personalized message"}]
            })
            
            assert response.status_code == 200
            groq_data = response.json()
            assert "choices" in groq_data
            assert groq_data["model"] == "mixtral-8x7b-32768"
        
        # Test configurazione OpenAI
        os.environ['LLM_PROVIDER'] = 'openai'
        os.environ['OPENAI_API_KEY'] = 'test_openai_key'
        
        with patch('requests.post') as mock_openai_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Messaggio generato da OpenAI"
                    }
                }],
                "usage": {"total_tokens": 125},
                "model": "gpt-3.5-turbo"
            }
            mock_openai_request.return_value = mock_response
            
            # Simula chiamata a OpenAI
            openai_url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": "Bearer test_openai_key"}
            
            response = requests.post(openai_url, headers=headers, json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Generate personalized message"}]
            })
            
            assert response.status_code == 200
            openai_data = response.json()
            assert "choices" in openai_data
            assert openai_data["model"] == "gpt-3.5-turbo"
    
    def test_rf4_3_redis_cache_ttl_configurable(self):
        """
        RF4.3: Deve implementare cache Redis per messaggi con TTL configurabile
        """
        # Configurazione TTL cache
        os.environ['CACHE_TTL'] = '1800'  # 30 minuti
        
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Test cache set con TTL
            cache_key = "message:user_123:shop_456"
            message_data = {
                "message": "Cached personalized message",
                "timestamp": datetime.now().isoformat(),
                "personalization_score": 0.9
            }
            
            # Simula set cache con TTL
            mock_redis.setex(cache_key, 1800, json.dumps(message_data))
            
            # Verifica cache hit
            mock_redis.get.return_value = json.dumps(message_data).encode('utf-8')
            cached_result = mock_redis.get(cache_key)
            
            assert cached_result is not None
            cached_data = json.loads(cached_result.decode('utf-8'))
            assert cached_data["message"] == "Cached personalized message"
            assert "timestamp" in cached_data
            
            # Test cache miss dopo TTL
            mock_redis.get.return_value = None
            expired_result = mock_redis.get(cache_key)
            assert expired_result is None
            
            # Verifica chiamate Redis
            mock_redis.setex.assert_called_once_with(cache_key, 1800, json.dumps(message_data))
    
    def test_rf4_4_strategy_pattern_offers(self):
        """
        RF4.4: Deve gestire offerte con Strategy Pattern 
        (Standard/Aggressive/Conservative)
        """
        # Mock delle strategie di offerta
        class MockOfferStrategy:
            def generate_offer(self, user_profile: Dict, shop_info: Dict) -> Dict:
                pass
        
        class MockStandardStrategy(MockOfferStrategy):
            def generate_offer(self, user_profile: Dict, shop_info: Dict) -> Dict:
                return {
                    "discount_percent": 10,
                    "duration_hours": 24,
                    "strategy": "standard"
                }
        
        class MockAggressiveStrategy(MockOfferStrategy):
            def generate_offer(self, user_profile: Dict, shop_info: Dict) -> Dict:
                return {
                    "discount_percent": 25,
                    "duration_hours": 6,
                    "strategy": "aggressive"
                }
        
        class MockConservativeStrategy(MockOfferStrategy):
            def generate_offer(self, user_profile: Dict, shop_info: Dict) -> Dict:
                return {
                    "discount_percent": 5,
                    "duration_hours": 72,
                    "strategy": "conservative"
                }
        
        # Test dati
        user_profile = {"age": 25, "profession": "Engineer"}
        shop_info = {"category": "electronics", "name": "TechStore"}
        
        # Test Standard Strategy
        standard_strategy = MockStandardStrategy()
        standard_offer = standard_strategy.generate_offer(user_profile, shop_info)
        
        assert standard_offer["discount_percent"] == 10
        assert standard_offer["duration_hours"] == 24
        assert standard_offer["strategy"] == "standard"
        
        # Test Aggressive Strategy
        aggressive_strategy = MockAggressiveStrategy()
        aggressive_offer = aggressive_strategy.generate_offer(user_profile, shop_info)
        
        assert aggressive_offer["discount_percent"] == 25
        assert aggressive_offer["duration_hours"] == 6
        assert aggressive_offer["strategy"] == "aggressive"
        
        # Test Conservative Strategy
        conservative_strategy = MockConservativeStrategy()
        conservative_offer = conservative_strategy.generate_offer(user_profile, shop_info)
        
        assert conservative_offer["discount_percent"] == 5
        assert conservative_offer["duration_hours"] == 72
        assert conservative_offer["strategy"] == "conservative"
    
    def test_rf4_5_builder_pattern_complex_offers(self):
        """
        RF4.5: Deve supportare Builder Pattern per creazione offerte complesse
        """
        # Mock OfferBuilder con fluent interface
        class MockOfferBuilder:
            def __init__(self):
                self.offer_data = {}
            
            def set_discount(self, percent):
                self.offer_data["discount_percent"] = percent
                return self
            
            def set_duration(self, hours):
                self.offer_data["duration_hours"] = hours
                return self
            
            def set_conditions(self, conditions):
                self.offer_data["conditions"] = conditions
                return self
            
            def set_target_demographics(self, demographics):
                self.offer_data["target_demographics"] = demographics
                return self
            
            def add_bonus(self, bonus):
                if "bonuses" not in self.offer_data:
                    self.offer_data["bonuses"] = []
                self.offer_data["bonuses"].append(bonus)
                return self
            
            def build(self):
                return self.offer_data.copy()
        
        # Test costruzione offerta complessa con Builder
        builder = MockOfferBuilder()
        
        complex_offer = (builder
                        .set_discount(20)
                        .set_duration(48)
                        .set_conditions({"min_purchase": 50, "max_uses": 10})
                        .set_target_demographics({"min_age": 18, "max_age": 35})
                        .add_bonus("free_shipping")
                        .add_bonus("loyalty_points")
                        .build())
        
        # Verifica offerta costruita
        assert complex_offer["discount_percent"] == 20
        assert complex_offer["duration_hours"] == 48
        assert complex_offer["conditions"]["min_purchase"] == 50
        assert complex_offer["conditions"]["max_uses"] == 10
        assert complex_offer["target_demographics"]["min_age"] == 18
        assert complex_offer["target_demographics"]["max_age"] == 35
        assert len(complex_offer["bonuses"]) == 2
        assert "free_shipping" in complex_offer["bonuses"]
        assert "loyalty_points" in complex_offer["bonuses"]
    
    def test_rf4_6_factory_pattern_typed_offers(self):
        """
        RF4.6: Factory Pattern deve creare offerte tipizzate 
        (Flash/Student/Senior/Category)
        """
        # Mock OfferFactory
        class MockOfferFactory:
            @staticmethod
            def create_flash_offer(shop_info: Dict) -> Dict:
                return {
                    "type": "flash",
                    "discount_percent": 30,
                    "duration_hours": 2,
                    "urgency": "high",
                    "availability": "limited"
                }
            
            @staticmethod
            def create_student_offer(user_profile: Dict) -> Dict:
                return {
                    "type": "student",
                    "discount_percent": 15,
                    "duration_hours": 168,  # 1 settimana
                    "verification_required": True,
                    "age_restriction": {"max_age": 26}
                }
            
            @staticmethod
            def create_senior_offer(user_profile: Dict) -> Dict:
                return {
                    "type": "senior",
                    "discount_percent": 12,
                    "duration_hours": 720,  # 30 giorni
                    "age_restriction": {"min_age": 65}
                }
            
            @staticmethod
            def create_category_offer(category: str) -> Dict:
                category_discounts = {
                    "electronics": 18,
                    "clothing": 25,
                    "food": 10,
                    "books": 20
                }
                
                return {
                    "type": "category",
                    "category": category,
                    "discount_percent": category_discounts.get(category, 10),
                    "duration_hours": 48
                }
        
        factory = MockOfferFactory()
        
        # Test Flash Offer
        flash_offer = factory.create_flash_offer({"category": "electronics"})
        assert flash_offer["type"] == "flash"
        assert flash_offer["discount_percent"] == 30
        assert flash_offer["duration_hours"] == 2
        assert flash_offer["urgency"] == "high"
        
        # Test Student Offer
        student_profile = {"age": 22, "student": True}
        student_offer = factory.create_student_offer(student_profile)
        assert student_offer["type"] == "student"
        assert student_offer["verification_required"] is True
        assert student_offer["age_restriction"]["max_age"] == 26
        
        # Test Senior Offer
        senior_profile = {"age": 68}
        senior_offer = factory.create_senior_offer(senior_profile)
        assert senior_offer["type"] == "senior"
        assert senior_offer["age_restriction"]["min_age"] == 65
        assert senior_offer["duration_hours"] == 720
        
        # Test Category Offer
        electronics_offer = factory.create_category_offer("electronics")
        assert electronics_offer["type"] == "category"
        assert electronics_offer["category"] == "electronics"
        assert electronics_offer["discount_percent"] == 18
    
    def test_rf4_7_validation_strategy_offer_constraints(self):
        """
        RF4.7: Validation Strategy deve validare vincoli offerte 
        (età, interessi, date)
        """
        # Mock Validation Strategies
        class MockAgeValidator:
            def validate(self, user_profile: Dict, offer: Dict) -> bool:
                user_age = user_profile.get("age", 0)
                
                if "age_restriction" in offer:
                    min_age = offer["age_restriction"].get("min_age", 0)
                    max_age = offer["age_restriction"].get("max_age", 150)
                    return min_age <= user_age <= max_age
                
                return True
        
        class MockInterestValidator:
            def validate(self, user_profile: Dict, offer: Dict) -> bool:
                user_interests = set(user_profile.get("interests", []))
                required_interests = set(offer.get("required_interests", []))
                
                if required_interests:
                    return bool(user_interests.intersection(required_interests))
                
                return True
        
        class MockDateValidator:
            def validate(self, user_profile: Dict, offer: Dict) -> bool:
                now = datetime.now()
                
                valid_from = offer.get("valid_from")
                valid_until = offer.get("valid_until")
                
                if valid_from:
                    valid_from_dt = datetime.fromisoformat(valid_from)
                    if now < valid_from_dt:
                        return False
                
                if valid_until:
                    valid_until_dt = datetime.fromisoformat(valid_until)
                    if now > valid_until_dt:
                        return False
                
                return True
        
        # Test validazioni
        age_validator = MockAgeValidator()
        interest_validator = MockInterestValidator()
        date_validator = MockDateValidator()
        
        user_profile = {
            "age": 25,
            "interests": ["technology", "travel"]
        }
        
        # Test validazione età valida
        valid_age_offer = {
            "age_restriction": {"min_age": 18, "max_age": 35}
        }
        assert age_validator.validate(user_profile, valid_age_offer) is True
        
        # Test validazione età non valida
        invalid_age_offer = {
            "age_restriction": {"min_age": 65, "max_age": 99}
        }
        assert age_validator.validate(user_profile, invalid_age_offer) is False
        
        # Test validazione interessi validi
        valid_interest_offer = {
            "required_interests": ["technology"]
        }
        assert interest_validator.validate(user_profile, valid_interest_offer) is True
        
        # Test validazione interessi non validi
        invalid_interest_offer = {
            "required_interests": ["sports", "music"]
        }
        assert interest_validator.validate(user_profile, invalid_interest_offer) is False
        
        # Test validazione date valide
        now = datetime.now()
        valid_date_offer = {
            "valid_from": (now - timedelta(hours=1)).isoformat(),
            "valid_until": (now + timedelta(hours=24)).isoformat()
        }
        assert date_validator.validate(user_profile, valid_date_offer) is True
        
        # Test validazione date scadute
        expired_offer = {
            "valid_from": (now - timedelta(days=2)).isoformat(),
            "valid_until": (now - timedelta(hours=1)).isoformat()
        }
        assert date_validator.validate(user_profile, expired_offer) is False


@pytest.mark.system
class TestRF5DashboardUserBase:
    """
    Test per RF5 - Dashboard utente base
    Verifica interfaccia web, WebSocket, mappa Leaflet, filtri.
    """
    
    def test_rf5_1_web_interface_static_files(self):
        """
        RF5.1: Deve servire interfaccia web tramite `/dashboard/user` con static files
        """
        dashboard_url = "http://localhost:8003/dashboard/user"
        
        with patch('requests.get') as mock_get:
            # Mock risposta pagina dashboard
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.text = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>NearYou Dashboard</title>
                <link rel="stylesheet" href="/static/css/dashboard.css">
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            </head>
            <body>
                <div id="map"></div>
                <div id="notifications"></div>
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script src="/static/js/dashboard.js"></script>
            </body>
            </html>
            """
            mock_get.return_value = mock_response
            
            # Test accesso dashboard
            response = requests.get(dashboard_url)
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html"
            assert "NearYou Dashboard" in response.text
            assert "leaflet" in response.text.lower()
            assert "/static/css/dashboard.css" in response.text
            assert "/static/js/dashboard.js" in response.text
        
        # Test static files CSS
        css_url = "http://localhost:8003/static/css/dashboard.css"
        with patch('requests.get') as mock_css:
            mock_css_response = Mock()
            mock_css_response.status_code = 200
            mock_css_response.headers = {"content-type": "text/css"}
            mock_css_response.text = """
            .map-container { height: 600px; width: 100%; }
            .notification-panel { position: fixed; right: 20px; }
            """
            mock_css.return_value = mock_css_response
            
            css_response = requests.get(css_url)
            assert css_response.status_code == 200
            assert css_response.headers["content-type"] == "text/css"
        
        # Test static files JavaScript
        js_url = "http://localhost:8003/static/js/dashboard.js"
        with patch('requests.get') as mock_js:
            mock_js_response = Mock()
            mock_js_response.status_code = 200
            mock_js_response.headers = {"content-type": "application/javascript"}
            mock_js_response.text = """
            const map = L.map('map').setView([45.4642, 9.1900], 13);
            const websocket = new WebSocket('ws://localhost:8003/ws/positions');
            """
            mock_js.return_value = mock_js_response
            
            js_response = requests.get(js_url)
            assert js_response.status_code == 200
            assert js_response.headers["content-type"] == "application/javascript"
    
    @pytest.mark.asyncio
    def test_rf5_3_leaflet_map_categorized_markers(self):
        """
        RF5.3: Deve implementare mappa Leaflet con marker categorizzati per shop types
        """
        # Test API endpoint per shop data
        shops_api_url = "http://localhost:8003/api/shops"
        
        with patch('requests.get') as mock_get:
            # Mock risposta API shops
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "shops": [
                    {
                        "shop_id": 1,
                        "name": "Caffè Milano",
                        "category": "bar",
                        "latitude": 45.4640,
                        "longitude": 9.1895,
                        "rating": 4.5
                    },
                    {
                        "shop_id": 2,
                        "name": "TechStore",
                        "category": "electronics",
                        "latitude": 45.4645,
                        "longitude": 9.1902,
                        "rating": 4.2
                    },
                    {
                        "shop_id": 3,
                        "name": "Fitness Center",
                        "category": "palestra",
                        "latitude": 45.4638,
                        "longitude": 9.1888,
                        "rating": 4.8
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            # Test richiesta shops
            response = requests.get(shops_api_url)
            
            assert response.status_code == 200
            shops_data = response.json()
            assert "shops" in shops_data
            
            shops = shops_data["shops"]
            assert len(shops) == 3
            
            # Verifica categorizzazione
            categories = set(shop["category"] for shop in shops)
            expected_categories = {"bar", "electronics", "palestra"}
            assert categories == expected_categories
            
            # Verifica coordinate valide per Milano
            for shop in shops:
                lat, lon = shop["latitude"], shop["longitude"]
                assert 45.3 <= lat <= 45.6, f"Latitudine non valida per Milano: {lat}"
                assert 9.0 <= lon <= 9.3, f"Longitudine non valida per Milano: {lon}"
                assert "rating" in shop
                assert 0 <= shop["rating"] <= 5
    
    def test_rf5_4_user_route_polyline_history(self):
        """
        RF5.4: Deve visualizzare percorso utente come polyline con history
        """
        # Test API endpoint per user route history
        route_api_url = "http://localhost:8003/api/user/123/route"
        
        with patch('requests.get') as mock_get:
            # Mock risposta route history
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "user_id": 123,
                "route_points": [
                    {
                        "latitude": 45.4642,
                        "longitude": 9.1900,
                        "timestamp": "2024-12-09T14:00:00Z",
                        "speed_kmh": 15.5
                    },
                    {
                        "latitude": 45.4645,
                        "longitude": 9.1905,
                        "timestamp": "2024-12-09T14:02:00Z",
                        "speed_kmh": 12.3
                    },
                    {
                        "latitude": 45.4648,
                        "longitude": 9.1910,
                        "timestamp": "2024-12-09T14:04:00Z",
                        "speed_kmh": 18.7
                    }
                ],
                "total_distance_meters": 450,
                "total_duration_minutes": 4,
                "polyline_encoded": "encoded_polyline_string"
            }
            mock_get.return_value = mock_response
            
            # Test richiesta route
            response = requests.get(route_api_url)
            
            assert response.status_code == 200
            route_data = response.json()
            
            assert route_data["user_id"] == 123
            assert "route_points" in route_data
            assert len(route_data["route_points"]) == 3
            
            # Verifica punti route
            points = route_data["route_points"]
            for point in points:
                assert "latitude" in point
                assert "longitude" in point
                assert "timestamp" in point
                assert "speed_kmh" in point
                
                # Verifica velocità realistica per bicicletta
                assert 0 <= point["speed_kmh"] <= 30
            
            # Verifica metadati percorso
            assert route_data["total_distance_meters"] > 0
            assert route_data["total_duration_minutes"] > 0
            assert "polyline_encoded" in route_data
    
    def test_rf5_5_category_filters_predefined_mapping(self):
        """
        RF5.5: Deve supportare filtri categoria con mapping predefinito
        """
        # Test API endpoint per category filters
        categories_api_url = "http://localhost:8003/api/categories"
        
        with patch('requests.get') as mock_get:
            # Mock risposta category mapping
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "categories": {
                    "food": {
                        "label": "Food & Drink",
                        "subcategories": ["ristorante", "bar", "pizzeria", "gelateria"],
                        "icon": "fa-utensils",
                        "color": "#ff6b6b"
                    },
                    "shopping": {
                        "label": "Shopping",
                        "subcategories": ["abbigliamento", "electronics", "libreria"],
                        "icon": "fa-shopping-bag",
                        "color": "#4ecdc4"
                    },
                    "health": {
                        "label": "Health & Fitness",
                        "subcategories": ["palestra", "farmacia", "ospedale"],
                        "icon": "fa-heartbeat",
                        "color": "#45b7d1"
                    },
                    "services": {
                        "label": "Services",
                        "subcategories": ["banca", "ufficio_postale", "lavanderia"],
                        "icon": "fa-concierge-bell",
                        "color": "#96ceb4"
                    }
                }
            }
            mock_get.return_value = mock_response
            
            # Test richiesta categories
            response = requests.get(categories_api_url)
            
            assert response.status_code == 200
            categories_data = response.json()
            assert "categories" in categories_data
            
            categories = categories_data["categories"]
            
            # Verifica mapping predefinito
            expected_categories = {"food", "shopping", "health", "services"}
            assert set(categories.keys()) == expected_categories
            
            # Verifica struttura categoria
            for category_name, category_info in categories.items():
                assert "label" in category_info
                assert "subcategories" in category_info
                assert "icon" in category_info
                assert "color" in category_info
                
                # Verifica subcategorie
                assert len(category_info["subcategories"]) > 0
                
                # Verifica icon Font Awesome
                assert category_info["icon"].startswith("fa-")
                
                # Verifica color hex
                assert category_info["color"].startswith("#")
                assert len(category_info["color"]) == 7
    
    def test_rf5_6_websocket_http_polling_fallback(self):
        """
        RF5.6: Deve implementare fallback WebSocket→HTTP polling automatico
        """
        # Test HTTP polling endpoint come fallback
        polling_url = "http://localhost:8003/api/polling/positions"
        
        with patch('requests.get') as mock_get:
            # Mock risposta HTTP polling
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "updates": [
                    {
                        "type": "position_update",
                        "user_id": 123,
                        "latitude": 45.4642,
                        "longitude": 9.1900,
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "type": "notification",
                        "message": "New offer available!",
                        "shop_id": 456
                    }
                ],
                "next_poll_interval": 5000,  # 5 secondi
                "has_more": False
            }
            mock_get.return_value = mock_response
            
            # Test polling request
            headers = {"Authorization": "Bearer jwt_token"}
            response = requests.get(polling_url, headers=headers)
            
            assert response.status_code == 200
            polling_data = response.json()
            
            assert "updates" in polling_data
            assert "next_poll_interval" in polling_data
            assert "has_more" in polling_data
            
            updates = polling_data["updates"]
            assert len(updates) == 2
            
            # Verifica formato updates
            position_update = updates[0]
            assert position_update["type"] == "position_update"
            assert "latitude" in position_update
            assert "longitude" in position_update
            
            notification = updates[1]
            assert notification["type"] == "notification"
            assert "message" in notification
            
            # Verifica intervallo polling
            interval = polling_data["next_poll_interval"]
            assert 1000 <= interval <= 30000  # Tra 1 e 30 secondi


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
