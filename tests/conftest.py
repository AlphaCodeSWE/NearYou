"""
Test configuration and fixtures for the NearYou test suite.
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables and configuration."""
    # Set test environment variables
    test_env = {
        "JWT_SECRET": "test_secret_key_for_testing_only",
        "JWT_ALGORITHM": "HS256",
        "POSTGRES_HOST": "test_postgres",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_DB": "test_nearyou",
        "CLICKHOUSE_HOST": "test_clickhouse",
        "CLICKHOUSE_PORT": "9000",
        "CLICKHOUSE_USER": "default",
        "CLICKHOUSE_PASSWORD": "",
        "CLICKHOUSE_DATABASE": "test_nearyou",
        "REDIS_HOST": "test_redis",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "",
        "KAFKA_BROKER": "test_kafka:9092",
        "MESSAGE_GENERATOR_URL": "http://test_message_generator:8000",
        "OSRM_URL": "http://test_osrm:5000"
    }
    
    # Set environment variables
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup environment variables after test
    for key in test_env.keys():
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection for testing."""
    with patch('psycopg2.connect') as mock_connect:
        mock_connection = Mock()
        mock_cursor = Mock()
        
        # Setup context manager behavior
        mock_connect.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_connect.return_value.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_connection.cursor.return_value.__exit__ = Mock(return_value=None)
        
        yield {
            'connection': mock_connection,
            'cursor': mock_cursor,
            'connect': mock_connect
        }


@pytest.fixture
def mock_clickhouse_client():
    """Mock ClickHouse client for testing."""
    with patch('clickhouse_driver.Client') as mock_ch_class:
        mock_client = Mock()
        mock_ch_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    with patch('redis.Redis') as mock_redis_class:
        mock_client = Mock()
        mock_redis_class.return_value = mock_client
        mock_client.ping.return_value = True
        yield mock_client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": 123,
        "username": "testuser",
        "age": 25,
        "profession": "Engineer",
        "interests": ["technology", "travel", "food"],
        "latitude": 45.4642,
        "longitude": 9.1900,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sample_shop_data():
    """Sample shop data for testing."""
    return {
        "shop_id": 456,
        "shop_name": "Test Shop Milano",
        "category": "ristorante",
        "latitude": 45.4640,
        "longitude": 9.1895,
        "description": "Authentic Italian restaurant",
        "rating": 4.5
    }


@pytest.fixture
def sample_offer_data():
    """Sample offer data for testing."""
    return {
        "offer_id": 789,
        "shop_id": 456,
        "discount_percent": 20,
        "description": "20% off on all main courses!",
        "offer_type": "percentage",
        "valid_from": datetime.now().date(),
        "valid_until": datetime.now().date() + timedelta(days=30),
        "is_active": True,
        "max_uses": 100,
        "current_uses": 0,
        "min_age": 18,
        "max_age": 65,
        "target_categories": ["food", "dining"]
    }


@pytest.fixture
def mock_database_connections():
    """Mock DatabaseConnections singleton for testing."""
    with patch('src.data_pipeline.operators.DatabaseConnections') as mock_db_class:
        mock_instance = Mock()
        mock_db_class.return_value = mock_instance
        mock_db_class._instance = mock_instance
        
        # Mock connection methods
        mock_instance.get_cached_message.return_value = None
        mock_instance.cache_message.return_value = None
        mock_instance.notify.return_value = None
        mock_instance.get_metrics.return_value = {
            "metrics": {"cache_hits": 0, "cache_misses": 0},
            "avg_processing_time": 0.0,
            "latest_processing_times": []
        }
        
        yield mock_instance


@pytest.fixture
def mock_message_generator_service():
    """Mock message generator service for testing."""
    with patch('httpx.AsyncClient') as mock_http:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "Welcome to our shop! Special offer available."
        }
        mock_client.post.return_value = mock_response
        mock_http.return_value = mock_client
        yield mock_client


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Pytest markers for categorizing tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "acceptance: Acceptance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "database: Tests requiring database")
    config.addinivalue_line("markers", "cache: Tests requiring cache")
    config.addinivalue_line("markers", "websocket: Tests for WebSocket functionality")


# Custom assertions
class CustomAssertions:
    """Custom assertion helpers for tests."""
    
    @staticmethod
    def assert_valid_coordinates(latitude, longitude):
        """Assert that coordinates are valid."""
        assert -90 <= latitude <= 90, f"Invalid latitude: {latitude}"
        assert -180 <= longitude <= 180, f"Invalid longitude: {longitude}"
    
    @staticmethod
    def assert_valid_offer(offer_dict):
        """Assert that offer data is valid."""
        required_fields = ["shop_id", "discount_percent", "description"]
        for field in required_fields:
            assert field in offer_dict, f"Missing required field: {field}"
        
        assert 0 <= offer_dict["discount_percent"] <= 100, "Invalid discount percentage"
        assert len(offer_dict["description"]) > 0, "Description cannot be empty"
    
    @staticmethod
    def assert_valid_user_profile(profile_dict):
        """Assert that user profile data is valid."""
        required_fields = ["user_id", "age"]
        for field in required_fields:
            assert field in profile_dict, f"Missing required field: {field}"
        
        assert profile_dict["age"] > 0, "Age must be positive"
        assert profile_dict["user_id"] > 0, "User ID must be positive"


# Add custom assertions to pytest namespace
@pytest.fixture
def custom_assert():
    """Provide custom assertion helpers."""
    return CustomAssertions()


# Test data generators
class TestDataGenerators:
    """Generators for test data."""
    
    @staticmethod
    def generate_user_positions(count=10, center_lat=45.4642, center_lon=9.1900, radius=0.01):
        """Generate random user positions around Milan center."""
        import random
        positions = []
        
        for i in range(count):
            lat_offset = random.uniform(-radius, radius)
            lon_offset = random.uniform(-radius, radius)
            
            positions.append({
                "user_id": 1000 + i,
                "latitude": center_lat + lat_offset,
                "longitude": center_lon + lon_offset,
                "timestamp": datetime.now().isoformat(),
                "age": random.randint(18, 70),
                "profession": f"Profession_{i}",
                "interests": f"interest_{i % 5}"
            })
        
        return positions
    
    @staticmethod
    def generate_shops(count=5, center_lat=45.4642, center_lon=9.1900, radius=0.005):
        """Generate random shops around Milan center."""
        import random
        categories = ["ristorante", "bar", "abbigliamento", "palestra", "farmacia"]
        shops = []
        
        for i in range(count):
            lat_offset = random.uniform(-radius, radius)
            lon_offset = random.uniform(-radius, radius)
            
            shops.append({
                "shop_id": 2000 + i,
                "shop_name": f"Shop {i}",
                "category": categories[i % len(categories)],
                "latitude": center_lat + lat_offset,
                "longitude": center_lon + lon_offset,
                "rating": round(random.uniform(3.0, 5.0), 1)
            })
        
        return shops


@pytest.fixture
def test_data_generators():
    """Provide test data generators."""
    return TestDataGenerators()


# Performance testing helpers
class PerformanceHelpers:
    """Helpers for performance testing."""
    
    @staticmethod
    def measure_time(func, *args, **kwargs):
        """Measure execution time of a function."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time
    
    @staticmethod
    async def measure_async_time(async_func, *args, **kwargs):
        """Measure execution time of an async function."""
        import time
        start_time = time.time()
        result = await async_func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time


@pytest.fixture
def performance_helpers():
    """Provide performance testing helpers."""
    return PerformanceHelpers()
