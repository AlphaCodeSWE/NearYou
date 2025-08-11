#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script showcasing the implemented design patterns:
1. Singleton Pattern - ConfigurationManager and CacheManager
2. Factory Pattern - CacheFactory for different cache types
3. Strategy Pattern - OfferGenerationStrategy with different implementations
4. Observer Pattern - DatabaseConnections with metrics and performance observers

This script demonstrates how the patterns work together in the NearYou application.
"""

import logging
import sys
import os

# Add src to path for imports
sys.path.append('/Users/alessandrodipasquale/Desktop/NearYou')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_singleton_pattern():
    """Demonstrate Singleton Pattern implementation."""
    print("\n" + "="*60)
    print("DEMO: Singleton Pattern")
    print("="*60)
    
    try:
        from src.configg import ConfigurationManager, get_config
        
        # Test singleton behavior
        config1 = ConfigurationManager()
        config2 = ConfigurationManager()
        config3 = get_config()
        
        # All should be the same instance
        assert config1 is config2 is config3, "Singleton instances should be identical"
        print("ConfigurationManager Singleton: All instances are identical")
        
        # Show some configuration values
        print(f"Environment: {config1.environment}")
        print(f"ClickHouse Host: {config1.clickhouse_host}")
        print(f"Cache enabled: {config1.cache_enabled}")
        
        # Test cache manager singleton
        from src.cache import CacheManager, cache_manager, initialize_cache, get_cache
        
        manager1 = CacheManager()
        manager2 = cache_manager
        
        assert manager1 is manager2, "CacheManager instances should be identical"
        print("CacheManager Singleton: All instances are identical")
        
        print("Singleton Pattern working correctly!")
        
    except Exception as e:
        print(f"Singleton Pattern demo failed: {e}")

def demo_factory_pattern():
    """Demonstrate Factory Pattern implementation."""
    print("\n" + "="*60)
    print("DEMO: Factory Pattern")
    print("="*60)
    
    try:
        from src.cache import CacheFactory, initialize_cache, get_cache
        
        # Test memory cache creation
        memory_cache = CacheFactory.create_cache("memory", default_ttl=3600)
        print(f"Created MemoryCache: {type(memory_cache).__name__}")
        
        # Test Redis cache creation (will fallback to memory if Redis not available)
        redis_cache = CacheFactory.create_cache("redis", 
                                                host="localhost", 
                                                port=6379, 
                                                default_ttl=7200)
        print(f"Created Redis/Fallback cache: {type(redis_cache).__name__}")
        
        # Test auto selection
        auto_cache = CacheFactory.create_cache("auto", default_ttl=86400)
        print(f"Created Auto-selected cache: {type(auto_cache).__name__}")
        
        # Test cache functionality
        test_key = "test_key"
        test_value = {"message": "Hello from cache!", "timestamp": "2024-01-01"}
        
        success = memory_cache.set(test_key, test_value, ttl=60)
        print(f"Cache set operation: {success}")
        
        retrieved = memory_cache.get(test_key)
        print(f"Cache get operation: {retrieved}")
        
        exists = memory_cache.exists(test_key)
        print(f"Cache exists check: {exists}")
        
        info = memory_cache.info()
        print(f"Cache info: {info}")
        
        print("Factory Pattern working correctly!")
        
    except Exception as e:
        print(f"Factory Pattern demo failed: {e}")

def demo_strategy_pattern():
    """Demonstrate Strategy Pattern implementation."""
    print("\n" + "="*60)
    print("DEMO: Strategy Pattern")
    print("="*60)
    
    try:
        from src.services.offers_service import (
            OfferStrategyFactory, 
            StandardOfferStrategy,
            AggressiveOfferStrategy,
            ConservativeOfferStrategy,
            OffersService
        )
        from src.configg import get_config
        
        config = get_config()
        postgres_config = config.get_postgres_config()
        
        # Test different strategies
        print("Creating different offer strategies...")
        
        # Standard strategy
        standard_strategy = OfferStrategyFactory.create_strategy("standard")
        print(f"Created StandardOfferStrategy: {type(standard_strategy).__name__}")
        
        # Aggressive strategy
        aggressive_strategy = OfferStrategyFactory.create_strategy("aggressive")
        print(f"Created AggressiveOfferStrategy: {type(aggressive_strategy).__name__}")
        
        # Conservative strategy
        conservative_strategy = OfferStrategyFactory.create_strategy("conservative")
        print(f"Created ConservativeOfferStrategy: {type(conservative_strategy).__name__}")
        
        # Test strategy behavior differences
        test_shop_id = 1
        test_shop_name = "Caffè Demo"
        test_category = "bar"
        
        print(f"\nGenerating offers for {test_shop_name} ({test_category}):")
        
        # Standard offers
        standard_offers = standard_strategy.generate_offers(test_shop_id, test_shop_name, test_category)
        print(f"Standard strategy generated {len(standard_offers)} offers")
        if standard_offers:
            for i, offer in enumerate(standard_offers[:2]):  # Show first 2
                print(f"   Offer {i+1}: {offer.discount_percent}% - {offer.description[:50]}...")
        
        # Aggressive offers
        aggressive_offers = aggressive_strategy.generate_offers(test_shop_id, test_shop_name, test_category)
        print(f"Aggressive strategy generated {len(aggressive_offers)} offers")
        if aggressive_offers:
            for i, offer in enumerate(aggressive_offers[:2]):  # Show first 2
                print(f"   Offer {i+1}: {offer.discount_percent}% - {offer.description[:50]}...")
        
        # Conservative offers
        conservative_offers = conservative_strategy.generate_offers(test_shop_id, test_shop_name, test_category)
        print(f"Conservative strategy generated {len(conservative_offers)} offers")
        if conservative_offers:
            for i, offer in enumerate(conservative_offers[:2]):  # Show first 2
                print(f"   Offer {i+1}: {offer.discount_percent}% - {offer.description[:50]}...")
        
        # Test strategy switching at runtime
        offers_service = OffersService(postgres_config, "standard")
        print(f"Created OffersService with initial strategy: {type(offers_service.strategy).__name__}")
        
        offers_service.set_strategy(aggressive_strategy)
        print(f"Switched to: {type(offers_service.strategy).__name__}")
        
        offers_service.set_strategy(conservative_strategy)
        print(f"Switched to: {type(offers_service.strategy).__name__}")
        
        print("Strategy Pattern working correctly!")
        
    except Exception as e:
        print(f"Strategy Pattern demo failed: {e}")

def demo_observer_pattern():
    """Demonstrate Observer Pattern implementation."""
    print("\n" + "="*60)
    print("DEMO: Observer Pattern")
    print("="*60)
    
    try:
        from src.data_pipeline.operators import (
            get_db_connections,
            MetricsObserver,
            PerformanceObserver
        )
        
        # Get singleton database connections (Subject)
        db_conn = get_db_connections()
        print(f"Created DatabaseConnections singleton with {len(db_conn._observers)} default observers")
        
        # Create additional observers
        custom_metrics = MetricsObserver()
        custom_performance = PerformanceObserver()
        
        print("Initial metrics:", custom_metrics.get_metrics())
        
        # Attach observers
        db_conn.attach(custom_metrics)
        db_conn.attach(custom_performance)
        print(f"Attached custom observers. Total observers: {len(db_conn._observers)}")
        
        # Simulate some events to trigger observer notifications
        print("\nSimulating events...")
        
        # Simulate processing events
        for i in range(5):
            event_id = f"event_{i}"
            db_conn.notify("processing_start", {"event_id": event_id})
            
            # Simulate some work
            import time
            time.sleep(0.01)  # 10ms processing time
            
            db_conn.notify("processing_end", {"event_id": event_id})
            db_conn.notify("event_processed", {"user_id": f"user_{i}"})
        
        # Simulate other events
        db_conn.notify("message_generated", {"user_id": "user_1", "shop_id": "shop_1"})
        db_conn.notify("visit_simulated", {"user_id": "user_2", "shop_id": "shop_2"})
        db_conn.notify("shop_found", {"shop_id": "shop_3", "distance": 150})
        db_conn.notify("cache_hit", {"user_id": "user_3", "shop_id": "shop_3"})
        db_conn.notify("cache_miss", {"user_id": "user_4", "shop_id": "shop_4"})
        db_conn.notify("error", {"error": "Test error", "function": "demo_function"})
        
        # Check metrics after events
        print("\nFinal metrics:")
        final_metrics = custom_metrics.get_metrics()
        for key, value in final_metrics.items():
            print(f"   {key}: {value}")
        
        # Check performance metrics
        avg_time = custom_performance.get_avg_processing_time()
        latest_times = custom_performance.get_latest_processing_times(3)
        print(f"\nAverage processing time: {avg_time:.4f}s")
        print(f"   Latest processing times: {[f'{t:.4f}s' for t in latest_times]}")
        
        # Test observer detachment
        db_conn.detach(custom_metrics)
        print(f"Detached custom metrics observer. Total observers: {len(db_conn._observers)}")
        
        # Get overall metrics from the database connections
        overall_metrics = db_conn.get_metrics()
        print(f"\nOverall system metrics: {overall_metrics}")
        
        print("Observer Pattern working correctly!")
        
    except Exception as e:
        print(f"Observer Pattern demo failed: {e}")

def demo_patterns_integration():
    """Demonstrate how all patterns work together."""
    print("\n" + "="*60)
    print("DEMO: Design Patterns Integration")
    print("="*60)
    
    try:
        from src.configg import get_config
        from src.cache import initialize_cache, get_cache
        from src.services.offers_service import OffersService, OfferStrategyFactory
        from src.data_pipeline.operators import get_db_connections
        
        print("Demonstrating integrated pattern usage...")
        
        # 1. Singleton: Get configuration
        config = get_config()
        print(f"Singleton - Configuration environment: {config.environment}")
        
        # 2. Factory: Initialize cache
        initialize_cache("auto", **config.get_redis_config())
        cache = get_cache()
        print(f"Factory - Cache type: {type(cache).__name__}")
        
        # 3. Strategy: Create offers service with different strategies
        postgres_config = config.get_postgres_config()
        
        # Test all strategies
        strategies = ["standard", "aggressive", "conservative"]
        for strategy_name in strategies:
            strategy = OfferStrategyFactory.create_strategy(strategy_name)
            offers_service = OffersService(postgres_config, strategy_name)
            print(f"Strategy - {strategy_name}: {type(strategy).__name__}")
        
        # 4. Observer: Get database connections with monitoring
        db_conn = get_db_connections()
        print(f"Observer - DatabaseConnections with {len(db_conn._observers)} observers")
        
        # Simulate a complete workflow
        print("\nSimulating complete workflow...")
        
        # Cache some data
        cache.set("demo_key", {"workflow": "complete", "step": 1}, ttl=300)
        cached_data = cache.get("demo_key")
        print(f"   Cache operation: {cached_data is not None}")
        
        # Notify observers about workflow steps
        db_conn.notify("event_processed", {"workflow": "demo"})
        db_conn.notify("message_generated", {"workflow": "demo"})
        db_conn.notify("visit_simulated", {"workflow": "demo"})
        
        # Get final metrics
        metrics = db_conn.get_metrics()
        print(f"   Final workflow metrics: Events={metrics['metrics']['events_processed']}")
        
        print("All design patterns integrated successfully!")
        
    except Exception as e:
        print(f"Pattern integration demo failed: {e}")

def main():
    """Run all design pattern demonstrations."""
    print("NearYou Design Patterns Demonstration")
    print("Showcasing: Singleton, Factory, Strategy, and Observer patterns")
    
    # Run all demos
    demo_singleton_pattern()
    demo_factory_pattern()
    demo_strategy_pattern()
    demo_observer_pattern()
    demo_patterns_integration()
    
    print("\n" + "="*60)
    print("Design Patterns Demo Complete!")
    print("="*60)
    print("""
Summary of implemented patterns:

1. Singleton Pattern:
   - ConfigurationManager: Single instance for app configuration
   - CacheManager: Single instance for cache management
   - DatabaseConnections: Single instance for DB connections

2. Factory Pattern:
   - CacheFactory: Creates different cache types (Redis/Memory/Auto)
   - OfferStrategyFactory: Creates different offer strategies

3. Strategy Pattern:
   - OfferGenerationStrategy: Different algorithms for offer generation
   - StandardOfferStrategy: Balanced approach
   - AggressiveOfferStrategy: High discounts, short duration
   - ConservativeOfferStrategy: Lower discounts, longer duration

4. Observer Pattern:
   - DatabaseConnections as Subject
   - MetricsObserver: Collects operational metrics
   - PerformanceObserver: Monitors processing performance

All patterns are integrated and working together to provide:
- Centralized configuration management
- Flexible caching solutions
- Pluggable offer generation strategies
- Real-time system monitoring
    """)

if __name__ == "__main__":
    main()
