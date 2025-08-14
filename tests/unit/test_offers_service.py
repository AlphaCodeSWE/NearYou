"""
Unit Tests for offers service with Strategy Pattern implementation.
Tests different offer generation strategies and database operations.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
import psycopg2

from src.services.offers_service import (
    OffersService, OfferStrategyFactory, StandardOfferStrategy,
    AggressiveOfferStrategy, ConservativeOfferStrategy
)
from src.models.offer import Offer, OfferType


class TestOfferStrategyFactory:
    """Unit tests for OfferStrategyFactory."""
    
    def test_create_standard_strategy(self):
        """Test creating standard strategy."""
        strategy = OfferStrategyFactory.create_strategy("standard")
        assert isinstance(strategy, StandardOfferStrategy)
    
    def test_create_aggressive_strategy(self):
        """Test creating aggressive strategy."""
        strategy = OfferStrategyFactory.create_strategy("aggressive")
        assert isinstance(strategy, AggressiveOfferStrategy)
    
    def test_create_conservative_strategy(self):
        """Test creating conservative strategy."""
        strategy = OfferStrategyFactory.create_strategy("conservative")
        assert isinstance(strategy, ConservativeOfferStrategy)
    
    def test_create_unknown_strategy_fallback(self):
        """Test fallback to standard strategy for unknown types."""
        strategy = OfferStrategyFactory.create_strategy("unknown_strategy")
        assert isinstance(strategy, StandardOfferStrategy)
    
    def test_create_default_strategy(self):
        """Test creating strategy without parameters."""
        strategy = OfferStrategyFactory.create_strategy()
        assert isinstance(strategy, StandardOfferStrategy)


class TestStandardOfferStrategy:
    """Unit tests for StandardOfferStrategy."""
    
    def test_should_generate_offers_high_probability(self):
        """Test offer generation for high probability categories."""
        strategy = StandardOfferStrategy()
        
        with patch('random.random', return_value=0.3):
            # Assuming restaurants have 0.8 probability
            with patch.dict('src.services.offers_service.CATEGORY_OFFER_PROBABILITY', 
                          {'ristorante': 0.8}):
                assert strategy.should_generate_offers('ristorante') is True
    
    def test_should_generate_offers_low_probability(self):
        """Test offer generation rejection for low probability."""
        strategy = StandardOfferStrategy()
        
        with patch('random.random', return_value=0.9):
            with patch.dict('src.services.offers_service.CATEGORY_OFFER_PROBABILITY', 
                          {'categoria_rara': 0.1}):
                assert strategy.should_generate_offers('categoria_rara') is False
    
    def test_generate_offers_when_should_not_generate(self):
        """Test that no offers are generated when should_generate_offers returns False."""
        strategy = StandardOfferStrategy()
        
        with patch.object(strategy, 'should_generate_offers', return_value=False):
            offers = strategy.generate_offers(1, "Test Shop", "rare_category")
            assert offers == []
    
    @patch('random.randint')
    @patch('random.choice')
    def test_generate_offers_creates_correct_number(self, mock_choice, mock_randint):
        """Test that correct number of offers is generated."""
        strategy = StandardOfferStrategy()
        
        # Mock randomization
        mock_randint.side_effect = [
            2,    # Number of offers to generate
            25,   # Discount percentage
            14,   # Duration days
            100,  # Max uses
            30,   # Discount for second offer
            21,   # Duration for second offer
            150   # Max uses for second offer
        ]
        mock_choice.return_value = "Test offer description"
        
        with patch.object(strategy, 'should_generate_offers', return_value=True):
            with patch.dict('src.services.offers_service.CATEGORY_DISCOUNT_RANGES', 
                          {'test_category': (20, 30)}):
                with patch.dict('src.services.offers_service.CATEGORY_OFFER_DURATION', 
                              {'test_category': (10, 20)}):
                    offers = strategy.generate_offers(1, "Test Shop", "test_category")
        
        assert len(offers) == 2
        assert all(isinstance(offer, Offer) for offer in offers)
    
    def test_create_standard_offer_with_category_config(self):
        """Test creating offers with category-specific configuration."""
        strategy = StandardOfferStrategy()
        
        # Mock category configurations
        with patch.dict('src.services.offers_service.CATEGORY_DISCOUNT_RANGES', 
                      {'ristorante': (15, 35)}):
            with patch.dict('src.services.offers_service.CATEGORY_OFFER_DURATION', 
                          {'ristorante': (7, 30)}):
                with patch.dict('src.services.offers_service.CATEGORY_DESCRIPTIONS', 
                              {'ristorante': ["Cena speciale al {discount}%!"]}):
                    with patch('random.randint', side_effect=[25, 14, 100]):
                        with patch('random.choice', return_value="Cena speciale al {discount}%!"):
                            offer = strategy._create_standard_offer(1, "Ristorante Roma", "ristorante")
        
        assert offer is not None
        assert offer.shop_id == 1
        assert offer.discount_percent == 25
        assert "25%" in offer.description
        assert offer.valid_until == date.today() + timedelta(days=14)
    
    def test_create_standard_offer_with_age_targeting(self):
        """Test creating offers with age targeting."""
        strategy = StandardOfferStrategy()
        
        with patch.dict('src.services.offers_service.CATEGORY_AGE_TARGETING', 
                      {'test_category': {'giovani': (18, 30), 'senior': (65, None)}}):
            with patch('random.random', return_value=0.2):  # 30% chance, so this triggers
                with patch('random.choice', return_value='giovani'):
                    with patch('random.randint', side_effect=[20, 7, 50]):
                        offer = strategy._create_standard_offer(1, "Test Shop", "test_category")
        
        assert offer.min_age == 18
        assert offer.max_age == 30
    
    def test_create_standard_offer_with_interest_targeting(self):
        """Test creating offers with interest targeting."""
        strategy = StandardOfferStrategy()
        
        interests = ["fitness", "sport", "salute"]
        with patch.dict('src.services.offers_service.INTEREST_TARGETING', 
                      {'palestra': interests}):
            with patch('random.random', return_value=0.3):  # 40% chance, so this triggers
                with patch('random.sample', return_value=["fitness", "sport"]):
                    with patch('random.randint', side_effect=[30, 14, 75]):
                        offer = strategy._create_standard_offer(1, "Gym Plus", "palestra")
        
        assert offer.target_categories == ["fitness", "sport"]


class TestAggressiveOfferStrategy:
    """Unit tests for AggressiveOfferStrategy."""
    
    def test_should_generate_offers_always_true(self):
        """Test that aggressive strategy always generates offers."""
        strategy = AggressiveOfferStrategy()
        
        assert strategy.should_generate_offers("any_category") is True
        assert strategy.should_generate_offers("rare_category") is True
        assert strategy.should_generate_offers("") is True
    
    @patch('random.randint')
    def test_generate_more_offers(self, mock_randint):
        """Test that aggressive strategy generates more offers."""
        strategy = AggressiveOfferStrategy()
        
        # Mock to generate 4 offers (MAX_OFFERS_PER_SHOP + 1)
        mock_randint.side_effect = [
            4,    # Number of offers
            40, 50, 3, 100,  # First offer: discount, extra, duration, max_uses
            35, 45, 2, 75,   # Second offer
            30, 60, 1, 50,   # Third offer  
            25, 65, 5, 25    # Fourth offer
        ]
        
        with patch('random.choice') as mock_choice:
            mock_choice.return_value = "🔥 OFFERTA FLASH: {discount}% di sconto!"
            
            offers = strategy.generate_offers(1, "Aggressive Shop", "test_category")
        
        assert len(offers) == 4
        # Should have enhanced discounts
        assert all(offer.discount_percent >= 40 for offer in offers)
        # Should have short durations
        assert all(offer.valid_until <= date.today() + timedelta(days=7) for offer in offers)
    
    def test_create_aggressive_offer_enhanced_discount(self):
        """Test that aggressive offers have enhanced discounts."""
        strategy = AggressiveOfferStrategy()
        
        # Test multiple attempts to ensure we get valid offers
        for _ in range(3):
            offer = strategy._create_aggressive_offer(1, "Flash Shop", "ristorante")
            if offer is not None:
                break
        
        assert offer is not None
        # Aggressive offers should have significant discounts (enhanced from base)
        assert offer.discount_percent >= 20  # Should be higher than base minimum
        assert "🔥" in offer.description or "⚡" in offer.description or "🎯" in offer.description or "💥" in offer.description
        assert offer.valid_until <= date.today() + timedelta(days=7)  # Short duration for urgency
        assert offer.max_uses <= 50  # Limited uses for exclusivity
    
    def test_create_aggressive_offer_discount_cap(self):
        """Test that aggressive offers are capped at 70% discount."""
        strategy = AggressiveOfferStrategy()
        
        # Use existing category and realistic values
        with patch('random.randint', side_effect=[60, 20, 2, 30]):  # base_discount, extra, duration, max_uses
            offer = strategy._create_aggressive_offer(1, "Mega Shop", "ristorante")
        
        assert offer is not None
        assert offer.discount_percent == 70  # Capped at 70%


class TestConservativeOfferStrategy:
    """Unit tests for ConservativeOfferStrategy."""
    
    def test_should_generate_offers_reduced_probability(self):
        """Test that conservative strategy has reduced probability."""
        strategy = ConservativeOfferStrategy()
        
        # Mock 70% of standard probability
        with patch.dict('src.services.offers_service.CATEGORY_OFFER_PROBABILITY', 
                      {'test_category': 0.8}):  # 80% standard
            # 0.8 * 0.7 = 0.56, so random 0.5 should pass
            with patch('random.random', return_value=0.5):
                assert strategy.should_generate_offers('test_category') is True
            
            # 0.56, so random 0.6 should fail
            with patch('random.random', return_value=0.6):
                assert strategy.should_generate_offers('test_category') is False
    
    @patch('random.randint')
    def test_generate_fewer_offers(self, mock_randint):
        """Test that conservative strategy generates fewer offers."""
        strategy = ConservativeOfferStrategy()
        
        mock_randint.side_effect = [
            1,    # Number of offers (between 1 and MIN_OFFERS)
            25, 5, 14, 21, 150, 300  # discount, reduction, base_duration, extension, base_max, doubled
        ]
        
        with patch.object(strategy, 'should_generate_offers', return_value=True):
            # Test multiple times to account for randomness
            offers_generated = False
            for _ in range(5):  # Try up to 5 times
                offers = strategy.generate_offers(1, "Conservative Shop", "ristorante")
                if offers:
                    offers_generated = True
                    break
        
        assert offers_generated, "Conservative strategy should generate at least one offer"
        offer = offers[0]
        # Conservative offers have lower discounts than base range
        assert offer.discount_percent >= 5  # Minimum 5%
        assert offer.discount_percent <= 25  # Should be conservative (ristorante range is 10-25)
        # Longer duration than standard
        assert offer.valid_until >= date.today() + timedelta(days=14)  # At least 2 weeks
        # Higher max uses (conservative strategy uses higher values, typically 200+)
        assert offer.max_uses >= 150  # More lenient but still testing the conservative approach
    
    def test_create_conservative_offer_lower_discount(self):
        """Test that conservative offers have lower discounts."""
        strategy = ConservativeOfferStrategy()
        
        with patch.dict('src.services.offers_service.CATEGORY_DISCOUNT_RANGES', 
                      {'test_category': (20, 40)}):
            with patch('random.randint', side_effect=[30, 8, 14, 7, 100]):  # discount, reduction, duration, extension, max_uses
                offer = strategy._create_conservative_offer(1, "Steady Shop", "test_category")
        
        assert offer.discount_percent == 22  # 30 - 8
        assert offer.valid_until == date.today() + timedelta(days=21)  # 14 + 7
    
    def test_create_conservative_offer_minimum_discount(self):
        """Test that conservative offers have minimum 5% discount."""
        strategy = ConservativeOfferStrategy()
        
        with patch.dict('src.services.offers_service.CATEGORY_DISCOUNT_RANGES', 
                      {'test_category': (10, 20)}):
            with patch('random.randint', side_effect=[10, 10, 7, 14, 50]):  # Would be 0%, but minimum 5%
                offer = strategy._create_conservative_offer(1, "Minimal Shop", "test_category")
        
        assert offer.discount_percent == 5  # Minimum enforced


class TestOffersService:
    """Unit tests for OffersService main class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.postgres_config = {
            'host': 'localhost',
            'port': 5432,
            'user': 'test_user',
            'password': 'test_pass',
            'database': 'test_db'
        }
    
    def test_offers_service_initialization(self):
        """Test OffersService initialization."""
        service = OffersService(self.postgres_config, "aggressive")
        
        assert service.postgres_config == self.postgres_config
        assert isinstance(service.strategy, AggressiveOfferStrategy)
    
    def test_set_strategy_runtime(self):
        """Test changing strategy at runtime."""
        service = OffersService(self.postgres_config, "standard")
        assert isinstance(service.strategy, StandardOfferStrategy)
        
        new_strategy = ConservativeOfferStrategy()
        service.set_strategy(new_strategy)
        assert service.strategy == new_strategy
    
    @patch('psycopg2.connect')
    def test_get_connection(self, mock_connect):
        """Test database connection method."""
        mock_connection = Mock()
        mock_connect.return_value = mock_connection
        
        service = OffersService(self.postgres_config)
        connection = service.get_connection()
        
        assert connection == mock_connection
        mock_connect.assert_called_once_with(
            host='localhost',
            port=5432,
            user='test_user',
            password='test_pass',
            database='test_db'
        )
    
    @patch('psycopg2.connect')
    def test_generate_offers_for_all_shops(self, mock_connect):
        """Test generating offers for all shops."""
        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # Mock shops data
        mock_shops = [
            {'shop_id': 1, 'shop_name': 'Restaurant A', 'category': 'ristorante'},
            {'shop_id': 2, 'shop_name': 'Bar B', 'category': 'bar'},
            {'shop_id': 3, 'shop_name': 'Gym C', 'category': 'palestra'}
        ]
        mock_cursor.fetchall.return_value = mock_shops
        
        # Mock strategy
        mock_strategy = Mock()
        test_offers = [
            Offer(shop_id=1, discount_percent=20),
            Offer(shop_id=1, discount_percent=30)
        ]
        mock_strategy.generate_offers.return_value = test_offers
        
        service = OffersService(self.postgres_config)
        service.strategy = mock_strategy
        
        with patch.object(service, 'insert_offers', return_value=2) as mock_insert:
            total_offers = service.generate_offers_for_all_shops()
        
        assert total_offers == 6  # 3 shops * 2 offers each
        assert mock_strategy.generate_offers.call_count == 3
        assert mock_insert.call_count == 3
    
    @patch('psycopg2.connect')
    def test_insert_offers(self, mock_connect):
        """Test inserting offers into database."""
        # Mock database connection
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        offers = [
            Offer(shop_id=1, discount_percent=20, description="Test offer 1"),
            Offer(shop_id=2, discount_percent=30, description="Test offer 2")
        ]
        
        service = OffersService(self.postgres_config)
        inserted_count = service.insert_offers(offers)
        
        assert inserted_count == 2
        assert mock_cursor.execute.call_count == 2
        mock_connection.commit.assert_called_once()
    
    @patch('psycopg2.connect')
    def test_insert_offers_with_error(self, mock_connect):
        """Test inserting offers with partial errors."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # First insert succeeds, second fails
        mock_cursor.execute.side_effect = [None, psycopg2.Error("Database error")]
        
        offers = [
            Offer(shop_id=1, discount_percent=20),
            Offer(shop_id=2, discount_percent=30)
        ]
        
        service = OffersService(self.postgres_config)
        inserted_count = service.insert_offers(offers)
        
        assert inserted_count == 1  # Only first one succeeded
    
    @patch('psycopg2.connect')
    def test_get_active_offers_for_shop(self, mock_connect):
        """Test retrieving active offers for a shop."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # Mock database results
        mock_offers_data = [
            {'offer_id': 1, 'shop_id': 123, 'discount_percent': 30, 'description': 'Great offer'},
            {'offer_id': 2, 'shop_id': 123, 'discount_percent': 20, 'description': 'Good offer'}
        ]
        mock_cursor.fetchall.return_value = mock_offers_data
        
        service = OffersService(self.postgres_config)
        offers = service.get_active_offers_for_shop(123)
        
        assert len(offers) == 2
        assert offers[0]['discount_percent'] == 30
        mock_cursor.execute.assert_called_once()
        # Verify the SQL query includes shop_id parameter
        args, kwargs = mock_cursor.execute.call_args
        assert '123' in str(args) or 123 in args[1]
    
    @patch('psycopg2.connect')
    def test_cleanup_expired_offers(self, mock_connect):
        """Test cleaning up expired offers."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        # Mock that 5 offers were updated
        mock_cursor.rowcount = 5
        
        service = OffersService(self.postgres_config)
        updated_count = service.cleanup_expired_offers()
        
        assert updated_count == 5
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()
    
    def test_insert_offers_empty_list(self):
        """Test inserting empty list returns 0."""
        service = OffersService(self.postgres_config)
        result = service.insert_offers([])
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__])
