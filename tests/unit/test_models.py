"""
Unit Tests for data models (Offer, UserVisit) and related utilities.
Tests Builder Pattern, Factory Pattern, and data validation.
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from src.models.offer import (
    Offer, OfferType, OfferBuilder, OfferFactory, UserVisit, OfferValidator
)


class TestOfferModel:
    """Unit tests for the Offer model."""
    
    def test_offer_creation_with_defaults(self):
        """Test creating an offer with default values."""
        offer = Offer(shop_id=1, discount_percent=20, description="Test offer")
        
        assert offer.shop_id == 1
        assert offer.discount_percent == 20
        assert offer.description == "Test offer"
        assert offer.offer_type == OfferType.PERCENTAGE.value
        assert offer.is_active is True
        assert offer.current_uses == 0
        assert offer.valid_from == date.today()
        assert offer.target_categories == []
    
    def test_offer_validation_valid_offer(self):
        """Test validation of a valid offer."""
        offer = Offer(
            shop_id=1,
            discount_percent=25,
            description="Valid offer",
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            min_age=18,
            max_age=65
        )
        
        assert offer.is_valid() is True
    
    def test_offer_validation_invalid_discount(self):
        """Test validation fails for invalid discount percentages."""
        # Negative discount
        offer1 = Offer(shop_id=1, discount_percent=-10)
        assert offer1.is_valid() is False
        
        # Discount over 100%
        offer2 = Offer(shop_id=1, discount_percent=150)
        assert offer2.is_valid() is False
    
    def test_offer_validation_invalid_dates(self):
        """Test validation fails for invalid date ranges."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            valid_from=date.today() + timedelta(days=10),
            valid_until=date.today()  # End date before start date
        )
        
        assert offer.is_valid() is False
    
    def test_offer_validation_invalid_age_range(self):
        """Test validation fails for invalid age ranges."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            min_age=65,
            max_age=18  # Min age greater than max age
        )
        
        assert offer.is_valid() is False
    
    def test_offer_custom_validator(self):
        """Test setting custom validator using Strategy pattern."""
        # Create a custom validator that always returns False
        custom_validator = Mock()
        custom_validator.validate.return_value = False
        
        offer = Offer(shop_id=1, discount_percent=20)
        offer.set_validator(custom_validator)
        
        assert offer.is_valid() is False
        custom_validator.validate.assert_called_once_with(offer)
    
    def test_offer_to_dict(self):
        """Test converting offer to dictionary."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            description="Test offer",
            target_categories=["food", "drinks"]
        )
        
        offer_dict = offer.to_dict()
        
        assert offer_dict['shop_id'] == 1
        assert offer_dict['discount_percent'] == 20
        assert offer_dict['description'] == "Test offer"
        assert offer_dict['target_categories'] == ["food", "drinks"]
        assert offer_dict['is_active'] is True
    
    def test_offer_from_dict(self):
        """Test creating offer from dictionary."""
        data = {
            'offer_id': 123,
            'shop_id': 1,
            'discount_percent': 25,
            'description': "Test offer",
            'target_categories': ["food"],
            'min_age': 18,
            'max_age': 65
        }
        
        offer = Offer.from_dict(data)
        
        assert offer.offer_id == 123
        assert offer.shop_id == 1
        assert offer.discount_percent == 25
        assert offer.target_categories == ["food"]
        assert offer.min_age == 18
        assert offer.max_age == 65
    
    def test_offer_is_valid_for_user_age_constraints(self):
        """Test user-specific validation with age constraints."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            min_age=18,
            max_age=65,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30)
        )
        
        # Valid age
        assert offer.is_valid_for_user(25, []) is True
        
        # Too young
        assert offer.is_valid_for_user(16, []) is False
        
        # Too old
        assert offer.is_valid_for_user(70, []) is False
    
    def test_offer_is_valid_for_user_interest_constraints(self):
        """Test user-specific validation with interest constraints."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            target_categories=["food", "dining"],
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30)
        )
        
        # Matching interests
        assert offer.is_valid_for_user(25, ["food", "sports"]) is True
        assert offer.is_valid_for_user(25, ["DINING", "travel"]) is True  # Case insensitive
        
        # No matching interests
        assert offer.is_valid_for_user(25, ["sports", "travel"]) is False
        
        # Empty target categories (should always match)
        offer.target_categories = []
        assert offer.is_valid_for_user(25, ["anything"]) is True
    
    def test_offer_is_valid_for_user_date_constraints(self):
        """Test user-specific validation with date constraints."""
        # Future offer
        future_offer = Offer(
            shop_id=1,
            discount_percent=20,
            valid_from=date.today() + timedelta(days=5),
            valid_until=date.today() + timedelta(days=10)
        )
        assert future_offer.is_valid_for_user(25, []) is False
        
        # Expired offer
        expired_offer = Offer(
            shop_id=1,
            discount_percent=20,
            valid_from=date.today() - timedelta(days=10),
            valid_until=date.today() - timedelta(days=1)
        )
        assert expired_offer.is_valid_for_user(25, []) is False
    
    def test_offer_is_valid_for_user_usage_constraints(self):
        """Test user-specific validation with usage limits."""
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            max_uses=10,
            current_uses=10,  # Already at limit
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30)
        )
        
        assert offer.is_valid_for_user(25, []) is False
        
        # Still available uses
        offer.current_uses = 5
        assert offer.is_valid_for_user(25, []) is True
    
    def test_offer_get_display_text(self):
        """Test display text generation for different offer types."""
        # Percentage offer
        percentage_offer = Offer(
            shop_id=1,
            discount_percent=25,
            offer_type=OfferType.PERCENTAGE.value
        )
        
        display = percentage_offer.get_display_text("Pizza Palace")
        assert "25%" in display
        assert "Pizza Palace" in display
        
        # BOGO offer
        bogo_offer = Offer(
            shop_id=1,
            offer_type=OfferType.BUY_ONE_GET_ONE.value
        )
        
        display = bogo_offer.get_display_text("Coffee Shop")
        assert "Compra 1 e prendi 2" in display
        assert "Coffee Shop" in display
        
        # Custom description
        custom_offer = Offer(
            shop_id=1,
            description="Special custom offer!",
            offer_type="custom"
        )
        
        display = custom_offer.get_display_text("Test Shop")
        assert "Special custom offer!" in display


class TestOfferBuilder:
    """Unit tests for the OfferBuilder (Builder Pattern)."""
    
    def test_builder_basic_construction(self):
        """Test basic offer construction with builder."""
        builder = OfferBuilder()
        offer = (builder
                .shop(123)
                .discount(25)
                .description("Builder test offer")
                .build())
        
        assert offer.shop_id == 123
        assert offer.discount_percent == 25
        assert offer.description == "Builder test offer"
    
    def test_builder_fluent_interface(self):
        """Test fluent interface of builder."""
        builder = OfferBuilder()
        
        # Should be able to chain methods
        offer = (builder
                .shop(1)
                .discount(30)
                .offer_type(OfferType.BUY_ONE_GET_ONE)
                .valid_for_days(7)
                .max_uses(50)
                .age_target(min_age=18, max_age=35)
                .interest_target(["food", "dining"])
                .active(True)
                .build())
        
        assert offer.shop_id == 1
        assert offer.discount_percent == 30
        assert offer.offer_type == OfferType.BUY_ONE_GET_ONE.value
        assert offer.max_uses == 50
        assert offer.min_age == 18
        assert offer.max_age == 35
        assert offer.target_categories == ["food", "dining"]
        assert offer.is_active is True
    
    def test_builder_valid_period(self):
        """Test setting validity period with builder."""
        start_date = date.today()
        end_date = start_date + timedelta(days=14)
        
        builder = OfferBuilder()
        offer = (builder
                .shop(1)
                .discount(20)
                .valid_period(start_date, end_date)
                .build())
        
        assert offer.valid_from == start_date
        assert offer.valid_until == end_date
    
    def test_builder_valid_for_days(self):
        """Test setting validity for number of days."""
        builder = OfferBuilder()
        offer = (builder
                .shop(1)
                .discount(20)
                .valid_for_days(10)
                .build())
        
        assert offer.valid_from == date.today()
        assert offer.valid_until == date.today() + timedelta(days=10)
    
    def test_builder_reset_after_build(self):
        """Test that builder resets after building."""
        builder = OfferBuilder()
        
        # Build first offer
        offer1 = (builder
                 .shop(1)
                 .discount(20)
                 .build())
        
        # Build second offer without explicit reset
        offer2 = (builder
                 .shop(2)
                 .discount(30)
                 .build())
        
        # Should be independent
        assert offer1.shop_id == 1
        assert offer1.discount_percent == 20
        assert offer2.shop_id == 2
        assert offer2.discount_percent == 30
    
    def test_builder_validation_on_build(self):
        """Test that builder validates on build."""
        builder = OfferBuilder()
        
        # Invalid offer (negative discount)
        with pytest.raises(ValueError, match="Cannot build invalid offer"):
            (builder
             .shop(1)
             .discount(-10)  # Invalid
             .build())
    
    def test_builder_unsafe_build(self):
        """Test unsafe build bypasses validation."""
        builder = OfferBuilder()
        
        # This should work even with invalid data
        offer = (builder
                .shop(1)
                .discount(-10)  # Invalid but should still build
                .build_unsafe())
        
        assert offer.discount_percent == -10
    
    def test_builder_manual_reset(self):
        """Test manual reset of builder."""
        builder = OfferBuilder()
        
        # Configure builder
        builder.shop(1).discount(20)
        
        # Reset manually
        builder.reset()
        
        # Build with new configuration
        offer = builder.shop(2).discount(30).build()
        
        assert offer.shop_id == 2
        assert offer.discount_percent == 30


class TestOfferFactory:
    """Unit tests for the OfferFactory (Factory Pattern)."""
    
    def test_create_flash_offer(self):
        """Test creating flash offers."""
        offer = OfferFactory.create_flash_offer(
            shop_id=1,
            shop_name="Flash Shop",
            discount=50,
            hours=48
        )
        
        assert offer.shop_id == 1
        assert offer.discount_percent == 50
        assert "FLASH" in offer.description
        assert "Flash Shop" in offer.description
        assert offer.max_uses == 50
        # 48 hours = 2 days
        assert offer.valid_until == date.today() + timedelta(days=2)
    
    def test_create_student_offer(self):
        """Test creating student-targeted offers."""
        offer = OfferFactory.create_student_offer(
            shop_id=2,
            shop_name="Student Cafe",
            discount=15
        )
        
        assert offer.shop_id == 2
        assert offer.discount_percent == 15
        assert "studenti" in offer.description.lower()
        assert "Student Cafe" in offer.description
        assert offer.min_age == 16
        assert offer.max_age == 30
        assert "studio" in offer.target_categories
        assert offer.valid_until == date.today() + timedelta(days=30)
    
    def test_create_senior_offer(self):
        """Test creating senior-targeted offers."""
        offer = OfferFactory.create_senior_offer(
            shop_id=3,
            shop_name="Senior Market",
            discount=20
        )
        
        assert offer.shop_id == 3
        assert offer.discount_percent == 20
        assert "senior" in offer.description.lower()
        assert offer.min_age == 65
        assert offer.max_age is None
        assert offer.valid_until == date.today() + timedelta(days=60)
    
    def test_create_category_offer(self):
        """Test creating category-specific offers."""
        offer = OfferFactory.create_category_offer(
            shop_id=4,
            shop_name="Italian Restaurant",
            category="ristorante",
            discount=25
        )
        
        assert offer.shop_id == 4
        assert offer.discount_percent == 25
        assert "ristorante" in offer.description.lower()
        assert "cucina" in offer.target_categories
        assert offer.valid_until == date.today() + timedelta(days=21)
    
    def test_create_category_offer_unknown_category(self):
        """Test creating offer for unknown category."""
        offer = OfferFactory.create_category_offer(
            shop_id=5,
            shop_name="Unknown Shop",
            category="unknown_category",
            discount=10
        )
        
        assert offer.shop_id == 5
        assert offer.discount_percent == 10
        # Should use the category name as interest
        assert "unknown_category" in offer.target_categories


class TestUserVisit:
    """Unit tests for the UserVisit model."""
    
    def test_user_visit_creation(self):
        """Test creating a user visit."""
        visit = UserVisit(
            user_id=123,
            shop_id=456,
            offer_id=789,
            estimated_spending=25.50,
            user_satisfaction=8
        )
        
        assert visit.user_id == 123
        assert visit.shop_id == 456
        assert visit.offer_id == 789
        assert visit.estimated_spending == 25.50
        assert visit.user_satisfaction == 8
        assert visit.offer_accepted is False  # Default
    
    def test_user_visit_post_init_calculations(self):
        """Test post-initialization calculations."""
        visit_start = datetime(2023, 6, 15, 14, 30)  # Thursday, 2:30 PM
        visit_end = datetime(2023, 6, 15, 15, 45)    # Thursday, 3:45 PM
        
        visit = UserVisit(
            user_id=1,
            shop_id=2,
            visit_start_time=visit_start,
            visit_end_time=visit_end
        )
        
        # Day of week: Thursday = 4 (Monday=1)
        assert visit.day_of_week == 4
        assert visit.hour_of_day == 14
        # Duration: 75 minutes
        assert visit.duration_minutes == 75
    
    def test_user_visit_to_dict(self):
        """Test converting user visit to dictionary."""
        visit_time = datetime.now()
        visit = UserVisit(
            user_id=1,
            shop_id=2,
            offer_id=3,
            visit_start_time=visit_time,
            offer_accepted=True,
            estimated_spending=30.0,
            user_age=25,
            user_profession="Engineer",
            shop_name="Test Shop"
        )
        
        visit_dict = visit.to_dict()
        
        assert visit_dict['user_id'] == 1
        assert visit_dict['shop_id'] == 2
        assert visit_dict['offer_id'] == 3
        assert visit_dict['offer_accepted'] is True
        assert visit_dict['estimated_spending'] == 30.0
        assert visit_dict['user_age'] == 25
        assert visit_dict['user_profession'] == "Engineer"
        assert visit_dict['shop_name'] == "Test Shop"
    
    def test_user_visit_partial_time_data(self):
        """Test user visit with only start time."""
        visit_start = datetime(2023, 6, 15, 14, 30)
        
        visit = UserVisit(
            user_id=1,
            shop_id=2,
            visit_start_time=visit_start,
            visit_end_time=None
        )
        
        assert visit.day_of_week == 4  # Thursday
        assert visit.hour_of_day == 14
        assert visit.duration_minutes == 0  # No end time


class TestOfferValidator:
    """Unit tests for OfferValidator implementations."""
    
    def test_default_validator_valid_offer(self):
        """Test default validator with valid offer."""
        validator = OfferValidator()
        offer = Offer(
            shop_id=1,
            discount_percent=25,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=30),
            min_age=18,
            max_age=65
        )
        
        assert validator.validate(offer) is True
    
    def test_default_validator_invalid_discount(self):
        """Test default validator with invalid discount."""
        validator = OfferValidator()
        
        # Negative discount
        offer1 = Offer(shop_id=1, discount_percent=-5)
        assert validator.validate(offer1) is False
        
        # Over 100% discount
        offer2 = Offer(shop_id=1, discount_percent=150)
        assert validator.validate(offer2) is False
    
    def test_default_validator_invalid_date_range(self):
        """Test default validator with invalid date range."""
        validator = OfferValidator()
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            valid_from=date.today() + timedelta(days=10),
            valid_until=date.today()  # End before start
        )
        
        assert validator.validate(offer) is False
    
    def test_default_validator_invalid_age_range(self):
        """Test default validator with invalid age range."""
        validator = OfferValidator()
        offer = Offer(
            shop_id=1,
            discount_percent=20,
            min_age=65,
            max_age=18  # Min > Max
        )
        
        assert validator.validate(offer) is False
    
    def test_custom_validator_protocol(self):
        """Test that custom validators work with protocol."""
        # Create custom validator that rejects all offers over 50% discount
        class StrictValidator:
            def validate(self, offer):
                return offer.discount_percent <= 50
        
        strict_validator = StrictValidator()
        
        # Valid under strict rules
        offer1 = Offer(shop_id=1, discount_percent=40)
        offer1.set_validator(strict_validator)
        assert offer1.is_valid() is True
        
        # Invalid under strict rules
        offer2 = Offer(shop_id=1, discount_percent=60)
        offer2.set_validator(strict_validator)
        assert offer2.is_valid() is False


if __name__ == "__main__":
    pytest.main([__file__])
