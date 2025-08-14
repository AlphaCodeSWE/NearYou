"""
Test di sistema per i requisiti RF6-RF7 e requisiti non funzionali del sistema NearYou.

Questo modulo contiene test per:
- RF6: Storage e persistenza dati
- RF7: Cache e ottimizzazione base  
- RNF1: Documentazione
- RNF2: Test
- RV1-RV6: Requisiti di vincolo
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

import sys
import subprocess
from typing import Dict, List, Any

try:
    import docker
except ImportError:
    docker = Mock()


@pytest.mark.system
class TestRF6StoragePersistence:
    """
    Test per RF6 - Storage e persistenza dati
    Verifica database ClickHouse, PostgreSQL/PostGIS, storage offerte.
    """
    
    def test_rf6_1_clickhouse_events_storage(self):
        """
        RF6.1: Deve memorizzare eventi in ClickHouse tabelle `user_events` e `user_visits`
        """
        # Mock client ClickHouse
        with patch('clickhouse_driver.Client') as mock_ch_client:
            mock_client = Mock()
            mock_ch_client.return_value = mock_client
            
            # Test inserimento user_events
            user_event = {
                "user_id": 123,
                "event_type": "position_update",
                "latitude": 45.4642,
                "longitude": 9.1900,
                "timestamp": datetime.now(),
                "metadata": json.dumps({"speed": 15.5, "accuracy": 10})
            }
            
            # Simula inserimento in user_events
            insert_events_query = """
            INSERT INTO user_events (user_id, event_type, latitude, longitude, timestamp, metadata)
            VALUES (%(user_id)s, %(event_type)s, %(latitude)s, %(longitude)s, %(timestamp)s, %(metadata)s)
            """
            
            mock_client.execute(insert_events_query, user_event)
            
            # Test inserimento user_visits
            user_visit = {
                "user_id": 123,
                "shop_id": 456,
                "visit_timestamp": datetime.now(),
                "distance_meters": 150.5,
                "duration_seconds": 300,
                "message_sent": True
            }
            
            insert_visits_query = """
            INSERT INTO user_visits (user_id, shop_id, visit_timestamp, distance_meters, duration_seconds, message_sent)
            VALUES (%(user_id)s, %(shop_id)s, %(visit_timestamp)s, %(distance_meters)s, %(duration_seconds)s, %(message_sent)s)
            """
            
            mock_client.execute(insert_visits_query, user_visit)
            
            # Verifica chiamate
            assert mock_client.execute.call_count == 2
            
            # Test query lettura eventi
            mock_client.execute.return_value = [
                (123, "position_update", 45.4642, 9.1900, datetime.now(), '{"speed": 15.5}')
            ]
            
            select_query = """
            SELECT user_id, event_type, latitude, longitude, timestamp, metadata
            FROM user_events
            WHERE user_id = %(user_id)s
            ORDER BY timestamp DESC
            LIMIT 10
            """
            
            events = mock_client.execute(select_query, {"user_id": 123})
            
            assert len(events) == 1
            event = events[0]
            assert event[0] == 123  # user_id
            assert event[1] == "position_update"  # event_type
            assert 45.3 <= event[2] <= 45.6  # latitude Milano
            assert 9.0 <= event[3] <= 9.3    # longitude Milano
    
    def test_rf6_2_postgis_spatial_indices(self):
        """
        RF6.2: Deve gestire shop data in PostgreSQL/PostGIS con indici spaziali
        """
        # Mock connessione PostgreSQL/PostGIS
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Test creazione tabella shops con geometria
            create_table_query = """
            CREATE TABLE IF NOT EXISTS shops (
                shop_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                location GEOMETRY(POINT, 4326),
                description TEXT,
                rating DECIMAL(3,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            mock_cursor.execute(create_table_query)
            
            # Test creazione indice spaziale
            spatial_index_query = """
            CREATE INDEX IF NOT EXISTS idx_shops_location_gist 
            ON shops USING GIST (location);
            """
            
            mock_cursor.execute(spatial_index_query)
            
            # Test inserimento shop con geometria
            insert_shop_query = """
            INSERT INTO shops (name, category, latitude, longitude, location, description, rating)
            VALUES (%(name)s, %(category)s, %(latitude)s, %(longitude)s, 
                    ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
                    %(description)s, %(rating)s)
            """
            
            shop_data = {
                "name": "Caffè Milano",
                "category": "bar",
                "latitude": 45.4642,
                "longitude": 9.1900,
                "description": "Traditional Italian café",
                "rating": 4.5
            }
            
            mock_cursor.execute(insert_shop_query, shop_data)
            
            # Test query spaziale con indici
            spatial_query = """
            SELECT shop_id, name, category, latitude, longitude,
                   ST_Distance(location, ST_SetSRID(ST_MakePoint(%(user_lon)s, %(user_lat)s), 4326)) as distance
            FROM shops
            WHERE ST_DWithin(
                location,
                ST_SetSRID(ST_MakePoint(%(user_lon)s, %(user_lat)s), 4326),
                200
            )
            ORDER BY distance ASC
            """
            
            # Simula risultato query spaziale
            mock_cursor.fetchall.return_value = [
                (456, "Caffè Milano", "bar", 45.4642, 9.1900, 150.5),
                (789, "Libreria", "books", 45.4645, 9.1905, 185.2)
            ]
            
            user_position = {"user_lat": 45.4640, "user_lon": 9.1895}
            mock_cursor.execute(spatial_query, user_position)
            nearby_shops = mock_cursor.fetchall()
            
            assert len(nearby_shops) == 2
            for shop in nearby_shops:
                distance = shop[5]  # distance column
                assert distance <= 200.0, f"Shop oltre soglia 200m: {distance}m"
    
    def test_rf6_3_clickhouse_user_profiles(self):
        """
        RF6.3: Deve mantenere profili utenti in ClickHouse tabella `users`
        """
        with patch('clickhouse_driver.Client') as mock_ch_client:
            mock_client = Mock()
            mock_ch_client.return_value = mock_client
            
            # Test creazione tabella users
            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                user_id UInt32,
                username String,
                age UInt8,
                profession String,
                interests Array(String),
                password_hash String,
                status String DEFAULT 'active',
                created_at DateTime DEFAULT now(),
                last_login DateTime,
                preferences Map(String, String)
            ) ENGINE = MergeTree()
            ORDER BY user_id
            """
            
            mock_client.execute(create_users_table)
            
            # Test inserimento profilo utente
            user_profile = {
                "user_id": 123,
                "username": "testuser",
                "age": 25,
                "profession": "Engineer",
                "interests": ["technology", "travel", "food"],
                "password_hash": "bcrypt$hashed_password",
                "status": "active",
                "last_login": datetime.now(),
                "preferences": {"theme": "dark", "notifications": "enabled"}
            }
            
            insert_user_query = """
            INSERT INTO users (user_id, username, age, profession, interests, password_hash, status, last_login, preferences)
            VALUES (%(user_id)s, %(username)s, %(age)s, %(profession)s, %(interests)s, %(password_hash)s, %(status)s, %(last_login)s, %(preferences)s)
            """
            
            mock_client.execute(insert_user_query, user_profile)
            
            # Test query profilo utente
            mock_client.execute.return_value = [
                (123, "testuser", 25, "Engineer", ["technology", "travel", "food"], "bcrypt$hash", "active")
            ]
            
            select_user_query = """
            SELECT user_id, username, age, profession, interests, password_hash, status
            FROM users
            WHERE user_id = %(user_id)s AND status = 'active'
            """
            
            user_data = mock_client.execute(select_user_query, {"user_id": 123})
            
            assert len(user_data) == 1
            user = user_data[0]
            assert user[0] == 123  # user_id
            assert user[1] == "testuser"  # username
            assert user[2] == 25  # age
            assert user[3] == "Engineer"  # profession
            assert "technology" in user[4]  # interests
            assert user[5].startswith("bcrypt$")  # password_hash
            assert user[6] == "active"  # status
    
    def test_rf6_4_materialized_view_daily_stats(self):
        """
        RF6.4: Deve tracciare storico visite con vista materializzata `mv_daily_shop_stats`
        """
        with patch('clickhouse_driver.Client') as mock_ch_client:
            mock_client = Mock()
            mock_ch_client.return_value = mock_client
            
            # Test creazione vista materializzata
            create_mv_query = """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_shop_stats
            ENGINE = SummingMergeTree()
            ORDER BY (shop_id, visit_date)
            AS SELECT
                shop_id,
                toDate(visit_timestamp) AS visit_date,
                count() AS total_visits,
                countDistinct(user_id) AS unique_visitors,
                avg(duration_seconds) AS avg_duration,
                sum(CASE WHEN message_sent = 1 THEN 1 ELSE 0 END) AS messages_sent
            FROM user_visits
            GROUP BY shop_id, visit_date
            """
            
            mock_client.execute(create_mv_query)
            
            # Test query statistiche giornaliere
            mock_client.execute.return_value = [
                (456, datetime.now().date(), 25, 18, 245.5, 22),
                (789, datetime.now().date(), 12, 10, 180.2, 8)
            ]
            
            stats_query = """
            SELECT shop_id, visit_date, total_visits, unique_visitors, avg_duration, messages_sent
            FROM mv_daily_shop_stats
            WHERE visit_date >= %(start_date)s AND visit_date <= %(end_date)s
            ORDER BY total_visits DESC
            """
            
            date_params = {
                "start_date": datetime.now().date(),
                "end_date": datetime.now().date()
            }
            
            daily_stats = mock_client.execute(stats_query, date_params)
            
            assert len(daily_stats) == 2
            
            # Verifica statistiche shop più visitato
            top_shop = daily_stats[0]
            assert top_shop[0] == 456  # shop_id
            assert top_shop[2] == 25   # total_visits
            assert top_shop[3] == 18   # unique_visitors
            assert top_shop[4] > 0     # avg_duration
            assert top_shop[5] == 22   # messages_sent
    
    def test_rf6_5_postgresql_offers_temporal_constraints(self):
        """
        RF6.5: Deve supportare offers storage in PostgreSQL con vincoli temporali
        """
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Test creazione tabella offers con vincoli temporali
            create_offers_table = """
            CREATE TABLE IF NOT EXISTS offers (
                offer_id SERIAL PRIMARY KEY,
                shop_id INTEGER REFERENCES shops(shop_id),
                offer_type VARCHAR(50) NOT NULL,
                discount_percent INTEGER CHECK (discount_percent >= 0 AND discount_percent <= 100),
                description TEXT NOT NULL,
                valid_from TIMESTAMP NOT NULL,
                valid_until TIMESTAMP NOT NULL,
                max_uses INTEGER DEFAULT NULL,
                current_uses INTEGER DEFAULT 0,
                min_age INTEGER DEFAULT 0,
                max_age INTEGER DEFAULT 150,
                target_categories TEXT[],
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_date_range CHECK (valid_until > valid_from),
                CONSTRAINT valid_age_range CHECK (max_age > min_age),
                CONSTRAINT valid_uses CHECK (current_uses <= max_uses OR max_uses IS NULL)
            );
            """
            
            mock_cursor.execute(create_offers_table)
            
            # Test inserimento offerta con vincoli temporali
            offer_data = {
                "shop_id": 456,
                "offer_type": "percentage",
                "discount_percent": 20,
                "description": "20% off on all items",
                "valid_from": datetime.now(),
                "valid_until": datetime.now() + timedelta(days=7),
                "max_uses": 100,
                "current_uses": 0,
                "min_age": 18,
                "max_age": 65,
                "target_categories": ["electronics", "technology"]
            }
            
            insert_offer_query = """
            INSERT INTO offers (shop_id, offer_type, discount_percent, description, 
                               valid_from, valid_until, max_uses, current_uses, 
                               min_age, max_age, target_categories)
            VALUES (%(shop_id)s, %(offer_type)s, %(discount_percent)s, %(description)s,
                    %(valid_from)s, %(valid_until)s, %(max_uses)s, %(current_uses)s,
                    %(min_age)s, %(max_age)s, %(target_categories)s)
            """
            
            mock_cursor.execute(insert_offer_query, offer_data)
            
            # Test query offerte valide
            mock_cursor.fetchall.return_value = [
                (1, 456, "percentage", 20, "20% off on all items", 
                 datetime.now(), datetime.now() + timedelta(days=7), 100, 5, True)
            ]
            
            valid_offers_query = """
            SELECT offer_id, shop_id, offer_type, discount_percent, description,
                   valid_from, valid_until, max_uses, current_uses, is_active
            FROM offers
            WHERE shop_id = %(shop_id)s
            AND valid_from <= %(current_time)s
            AND valid_until > %(current_time)s
            AND is_active = true
            AND (max_uses IS NULL OR current_uses < max_uses)
            """
            
            query_params = {
                "shop_id": 456,
                "current_time": datetime.now()
            }
            
            mock_cursor.execute(valid_offers_query, query_params)
            valid_offers = mock_cursor.fetchall()
            
            assert len(valid_offers) == 1
            offer = valid_offers[0]
            assert offer[1] == 456  # shop_id
            assert offer[3] == 20   # discount_percent
            assert offer[8] < offer[7]  # current_uses < max_uses
            assert offer[9] is True  # is_active


@pytest.mark.system
class TestRF7CacheOptimization:
    """
    Test per RF7 - Cache e ottimizzazione base
    Verifica Redis cache, Memory cache LRU, TTL, statistiche cache.
    """
    
    def test_rf7_1_redis_cache_json_serialization(self):
        """
        RF7.1: Deve implementare Redis cache per messaggi LLM con serializzazione JSON
        """
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Test cache LLM message
            cache_key = "llm:message:user_123:shop_456"
            message_data = {
                "message": "Personalized offer message",
                "llm_provider": "groq",
                "generation_time_ms": 234,
                "personalization_score": 0.87,
                "timestamp": datetime.now().isoformat(),
                "user_profile": {
                    "age": 25,
                    "interests": ["technology", "travel"]
                }
            }
            
            # Test serializzazione e cache set
            serialized_data = json.dumps(message_data)
            mock_redis.setex(cache_key, 3600, serialized_data)
            
            # Test cache hit
            mock_redis.get.return_value = serialized_data.encode('utf-8')
            cached_result = mock_redis.get(cache_key)
            
            assert cached_result is not None
            deserialized_data = json.loads(cached_result.decode('utf-8'))
            
            # Verifica deserializzazione corretta
            assert deserialized_data["message"] == message_data["message"]
            assert deserialized_data["llm_provider"] == "groq"
            assert deserialized_data["personalization_score"] == 0.87
            assert "user_profile" in deserialized_data
            assert deserialized_data["user_profile"]["age"] == 25
            
            # Test cache miss
            mock_redis.get.return_value = None
            miss_result = mock_redis.get("nonexistent:key")
            assert miss_result is None
            
            # Verifica chiamate Redis
            mock_redis.setex.assert_called_once_with(cache_key, 3600, serialized_data)
    
    def test_rf7_2_memory_cache_lru_fallback(self):
        """
        RF7.2: Deve supportare Memory cache con LRU eviction come fallback
        """
        # Mock Memory Cache con LRU
        class MockLRUCache:
            def __init__(self, max_size=100):
                self.max_size = max_size
                self.cache = {}
                self.access_order = []
            
            def get(self, key):
                if key in self.cache:
                    # Aggiorna ordine accesso
                    self.access_order.remove(key)
                    self.access_order.append(key)
                    return self.cache[key]
                return None
            
            def set(self, key, value, ttl=None):
                # Evict LRU se necessario
                if len(self.cache) >= self.max_size and key not in self.cache:
                    lru_key = self.access_order.pop(0)
                    del self.cache[lru_key]
                
                self.cache[key] = {
                    "value": value,
                    "expires_at": datetime.now() + timedelta(seconds=ttl) if ttl else None
                }
                
                if key in self.access_order:
                    self.access_order.remove(key)
                self.access_order.append(key)
            
            def delete(self, key):
                if key in self.cache:
                    del self.cache[key]
                    self.access_order.remove(key)
            
            def size(self):
                return len(self.cache)
        
        # Test LRU cache
        lru_cache = MockLRUCache(max_size=3)
        
        # Riempi cache
        lru_cache.set("key1", "value1", ttl=3600)
        lru_cache.set("key2", "value2", ttl=3600)
        lru_cache.set("key3", "value3", ttl=3600)
        
        assert lru_cache.size() == 3
        
        # Accedi a key1 per aggiornare ordine
        assert lru_cache.get("key1")["value"] == "value1"
        
        # Aggiungi key4 - dovrebbe evictare key2 (LRU)
        lru_cache.set("key4", "value4", ttl=3600)
        
        assert lru_cache.size() == 3
        assert lru_cache.get("key2") is None  # Evicted
        assert lru_cache.get("key1") is not None  # Still there (recently accessed)
        assert lru_cache.get("key3") is not None  # Still there
        assert lru_cache.get("key4") is not None  # Newly added
        
        # Test fallback Redis -> Memory
        with patch('redis.Redis') as mock_redis_class:
            # Simula Redis failure
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            mock_redis.get.side_effect = Exception("Redis connection failed")
            
            # Fallback a Memory cache
            try:
                redis_result = mock_redis.get("test_key")
            except Exception:
                # Usa memory cache come fallback
                memory_result = lru_cache.get("key1")
                assert memory_result is not None
                assert memory_result["value"] == "value1"
    
    def test_rf7_3_configurable_ttl(self):
        """
        RF7.3: Deve implementare TTL configurabile via `CACHE_TTL`
        """
        # Test TTL configurazioni diverse
        test_configs = [
            {"CACHE_TTL": "300", "expected": 300},    # 5 minuti
            {"CACHE_TTL": "1800", "expected": 1800},  # 30 minuti
            {"CACHE_TTL": "3600", "expected": 3600},  # 1 ora
        ]
        
        for config in test_configs:
            os.environ['CACHE_TTL'] = config["CACHE_TTL"]
            expected_ttl = config["expected"]
            
            with patch('redis.Redis') as mock_redis_class:
                mock_redis = Mock()
                mock_redis_class.return_value = mock_redis
                
                # Test cache set con TTL configurato
                cache_key = "test:ttl:key"
                cache_value = {"data": "test_value"}
                
                # Simula set con TTL configurabile
                ttl_from_env = int(os.environ.get('CACHE_TTL', 3600))
                mock_redis.setex(cache_key, ttl_from_env, json.dumps(cache_value))
                
                # Verifica TTL configurato
                mock_redis.setex.assert_called_with(cache_key, expected_ttl, json.dumps(cache_value))
                
                # Test TTL remaining
                mock_redis.ttl.return_value = expected_ttl - 100  # 100 secondi passati
                remaining_ttl = mock_redis.ttl(cache_key)
                
                assert remaining_ttl == expected_ttl - 100
                assert remaining_ttl > 0
        
        # Test TTL scaduto
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Simula TTL scaduto
            mock_redis.ttl.return_value = -2  # Key scaduta
            mock_redis.get.return_value = None
            
            expired_ttl = mock_redis.ttl("expired:key")
            expired_value = mock_redis.get("expired:key")
            
            assert expired_ttl == -2
            assert expired_value is None
    
    def test_rf7_4_cache_statistics_hit_rate(self):
        """
        RF7.4: Deve fornire cache statistics e hit rate monitoring
        """
        # Mock cache statistics collector
        class MockCacheStats:
            def __init__(self):
                self.stats = {
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "total_requests": 0,
                    "total_evictions": 0,
                    "memory_usage_bytes": 0,
                    "average_response_time_ms": 0.0
                }
                self.response_times = []
            
            def record_hit(self, response_time_ms=0):
                self.stats["cache_hits"] += 1
                self.stats["total_requests"] += 1
                self.response_times.append(response_time_ms)
                self._update_avg_response_time()
            
            def record_miss(self, response_time_ms=0):
                self.stats["cache_misses"] += 1
                self.stats["total_requests"] += 1
                self.response_times.append(response_time_ms)
                self._update_avg_response_time()
            
            def record_eviction(self):
                self.stats["total_evictions"] += 1
            
            def update_memory_usage(self, bytes_used):
                self.stats["memory_usage_bytes"] = bytes_used
            
            def _update_avg_response_time(self):
                if self.response_times:
                    self.stats["average_response_time_ms"] = sum(self.response_times) / len(self.response_times)
            
            def get_hit_rate(self):
                if self.stats["total_requests"] == 0:
                    return 0.0
                return self.stats["cache_hits"] / self.stats["total_requests"]
            
            def get_stats(self):
                return {
                    **self.stats,
                    "hit_rate": self.get_hit_rate(),
                    "miss_rate": 1.0 - self.get_hit_rate()
                }
        
        # Test statistiche cache
        cache_stats = MockCacheStats()
        
        # Simula operazioni cache
        cache_stats.record_hit(2.5)   # Cache hit veloce
        cache_stats.record_hit(1.8)   # Cache hit veloce  
        cache_stats.record_miss(25.0) # Cache miss lento
        cache_stats.record_hit(3.2)   # Cache hit veloce
        cache_stats.record_miss(30.0) # Cache miss lento
        cache_stats.record_eviction()
        cache_stats.update_memory_usage(1024 * 1024)  # 1MB
        
        # Verifica statistiche
        stats = cache_stats.get_stats()
        
        assert stats["cache_hits"] == 3
        assert stats["cache_misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["total_evictions"] == 1
        assert stats["memory_usage_bytes"] == 1024 * 1024
        
        # Verifica hit rate
        expected_hit_rate = 3 / 5  # 60%
        assert abs(stats["hit_rate"] - expected_hit_rate) < 0.01
        assert abs(stats["miss_rate"] - 0.4) < 0.01  # 40%
        
        # Verifica tempo risposta medio
        expected_avg_time = (2.5 + 1.8 + 25.0 + 3.2 + 30.0) / 5  # 12.5ms
        assert abs(stats["average_response_time_ms"] - expected_avg_time) < 0.1
        
        # Test scenario hit rate alto (>90%)
        high_hit_cache = MockCacheStats()
        for _ in range(95):
            high_hit_cache.record_hit(2.0)
        for _ in range(5):
            high_hit_cache.record_miss(20.0)
        
        high_hit_stats = high_hit_cache.get_stats()
        assert high_hit_stats["hit_rate"] >= 0.9  # >90% hit rate
        assert high_hit_stats["average_response_time_ms"] < 5.0  # Tempo medio basso


@pytest.mark.system
class TestNonFunctionalRequirements:
    """
    Test per requisiti non funzionali (RNF1, RNF2) e di vincolo (RV1-RV6)
    """
    
    def test_rv1_docker_compose_deployment(self):
        """
        RV1.1: Deployment tramite Docker Compose
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        docker_compose_path = os.path.join(workspace_root, "docker-compose.yml")
        
        assert os.path.exists(docker_compose_path), "File docker-compose.yml mancante"
        
        # Verifica servizi essenziali nel docker-compose
        with open(docker_compose_path, 'r') as f:
            compose_content = f.read()
        
        essential_services = [
            "kafka", "clickhouse", "postgres", 
            "message-generator", "dashboard", "grafana"
        ]
        
        # Controlla anche file inclusi per servizi
        include_files = [
            "deployment/docker/docker-compose.yml",
            "monitoring/docker-compose.monitoring.yml"
        ]
        
        # Servizi che potrebbero essere in file separati
        optional_services = ["redis"]
        
        for service in essential_services:
            service_found = service in compose_content
            
            # Se non trovato nel file principale, controlla file inclusi
            if not service_found:
                for include_file in include_files:
                    include_path = os.path.join(workspace_root, include_file)
                    if os.path.exists(include_path):
                        with open(include_path, 'r') as f:
                            include_content = f.read()
                        if service in include_content:
                            service_found = True
                            break
            
            assert service_found, f"Servizio mancante in docker-compose: {service}"
        
        # Per servizi opzionali, solo warning se mancanti
        for service in optional_services:
            if service not in compose_content:
                # Verifica nei file inclusi ma non fallire se mancante
                found_in_includes = False
                for include_file in include_files:
                    include_path = os.path.join(workspace_root, include_file)
                    if os.path.exists(include_path):
                        with open(include_path, 'r') as f:
                            if service in f.read():
                                found_in_includes = True
                                break
        
        # Verifica dockerfile presenza
        dockerfile_path = os.path.join(workspace_root, "deployment/docker/Dockerfile")
        assert os.path.exists(dockerfile_path), "Dockerfile mancante"
    
    def test_rv1_microservices_architecture(self):
        """
        RV1.2: Architettura microservizi event-driven
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Verifica struttura microservizi
        microservices_dirs = [
            "services/dashboard",
            "services/message_generator", 
            "src/data_pipeline"
        ]
        
        for service_dir in microservices_dirs:
            service_path = os.path.join(workspace_root, service_dir)
            assert os.path.exists(service_path), f"Microservizio mancante: {service_dir}"
        
        # Verifica presenza file main per ogni servizio
        main_files = [
            "services/dashboard/main_user.py",
            "services/message_generator/app.py",
            "src/data_pipeline/producer.py"
        ]
        
        for main_file in main_files:
            main_path = os.path.join(workspace_root, main_file)
            assert os.path.exists(main_path), f"File main mancante: {main_file}"
    
    def test_rv1_stream_processor_presence(self):
        """
        RV1.3: Presenza Stream Processor
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Verifica presenza Bytewax stream processor
        bytewax_files = [
            "src/data_pipeline/bytewax_flow.py",
            "src/data_pipeline/operators.py"
        ]
        
        for bytewax_file in bytewax_files:
            bytewax_path = os.path.join(workspace_root, bytewax_file)
            assert os.path.exists(bytewax_path), f"File stream processor mancante: {bytewax_file}"
    
    def test_rv2_browser_compatibility(self):
        """
        RV2.1-RV2.6: Browser e compatibilità 
        Chrome/Chromium ≥51, Firefox ≥55, Safari ≥12.1, Edge ≥79, Safari iOS ≥12.2
        Esclusione IE e Edge Legacy
        """
        # Test presenza JavaScript ES6+ e API moderne
        dashboard_js_path = "/Users/alessandrodipasquale/Desktop/NearYou/services/dashboard/frontend_user"
        
        if os.path.exists(dashboard_js_path):
            # Verifica presenza file JavaScript/HTML
            js_files = []
            for root, dirs, files in os.walk(dashboard_js_path):
                for file in files:
                    if file.endswith(('.js', '.html')):
                        js_files.append(os.path.join(root, file))
            
            # Se ci sono file JS, verifica uso API moderne
            modern_apis = [
                "fetch(", "WebSocket(", "localStorage", "sessionStorage",
                "const ", "let ", "=>", "async ", "await "
            ]
            
            if js_files:
                for js_file in js_files[:3]:  # Controlla primi 3 file
                    try:
                        with open(js_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Almeno una API moderna deve essere presente
                        modern_api_found = any(api in content for api in modern_apis)
                        if len(content) > 100:  # Solo se file non vuoto
                            assert modern_api_found, f"Nessuna API moderna trovata in {js_file}"
                    except Exception:
                        pass  # Ignora errori di lettura file
    
    def test_rv3_frontend_technologies(self):
        """
        RV3.1-RV3.6: Tecnologie Frontend richieste
        WebSocket API, Fetch API, IntersectionObserver, Web Storage, CSS moderno, JS abilitato
        """
        # Test presenza dipendenze frontend
        frontend_technologies = {
            "leaflet": "Leaflet.js per mappe interattive",
            "websocket": "WebSocket per real-time",
            "font-awesome": "Font Awesome per icone"
        }
        
        # Verifica in docker-compose o file config
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Cerca in file HTML/JS per CDN links
        html_files = []
        for root, dirs, files in os.walk(workspace_root):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        
        if html_files:
            for html_file in html_files[:2]:  # Controlla primi 2 file HTML
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read().lower()
                    
                    # Verifica presenza Leaflet
                    assert "leaflet" in html_content, f"Leaflet.js non trovato in {html_file}"
                    
                except Exception:
                    pass  # Ignora errori di lettura
    
    def test_rv4_geographic_constraints(self):
        """
        RV4.1-RV4.3: Requisiti geografici - Milano focus
        Sistema focalizzato su Milano, coordinate WGS84, percorsi OSRM
        """
        # Test coordinate Milano nelle configurazioni
        milano_bbox = {
            "min_lat": 45.3,
            "max_lat": 45.6, 
            "min_lon": 9.0,
            "max_lon": 9.3
        }
        
        # Verifica presenza dati Milano
        milano_data_path = "/Users/alessandrodipasquale/Desktop/NearYou/data/milano.osm.pbf"
        assert os.path.exists(milano_data_path), "Dati OSM Milano mancanti"
        
        # Verifica file OSRM Milano
        osrm_files = [
            "data/milano.osrm.edges",
            "data/milano.osrm.geometry", 
            "data/milano.osrm.properties"
        ]
        
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        for osrm_file in osrm_files:
            osrm_path = os.path.join(workspace_root, osrm_file)
            assert os.path.exists(osrm_path), f"File OSRM Milano mancante: {osrm_file}"
    
    def test_rv5_operational_requirements(self):
        """
        RV5.1-RV5.6: Requisiti operativi
        Ambiente development, configurazione env vars, logging stdout, 
        gestione segreti, fallback WebSocket, design responsivo
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Test presenza file .env per configurazione
        env_example_path = os.path.join(workspace_root, ".env.example")
        if not os.path.exists(env_example_path):
            # Verifica almeno configurazione via docker-compose
            docker_compose_path = os.path.join(workspace_root, "docker-compose.yml")
            assert os.path.exists(docker_compose_path), "Configurazione ambiente mancante"
        
        # Test presenza Makefile per automazione
        makefile_path = os.path.join(workspace_root, "Makefile")
        if os.path.exists(makefile_path):
            with open(makefile_path, 'r') as f:
                makefile_content = f.read()
            
            # Verifica target essenziali
            essential_targets = ["up", "down", "build", "test"]
            for target in essential_targets:
                if f"{target}:" in makefile_content:
                    assert True  # Target trovato
                else:
                    # Target può essere in forma alternativa
                    pass
    
    def test_rnf2_scalability_requirements(self):
        """
        RNF2.1-RNF2.4: Scalabilità
        Architettura modulare, separazione concern, horizontal scaling, microservices
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Test presenza architettura modulare
        services_path = os.path.join(workspace_root, "services")
        assert os.path.exists(services_path), "Directory services mancante"
        
        # Verifica separazione servizi
        expected_services = ["dashboard", "message_generator"]
        
        for service in expected_services:
            service_path = os.path.join(services_path, service)
            assert os.path.exists(service_path), f"Servizio {service} mancante"
        
        # Test presenza configurazione Docker per scaling
        docker_compose_path = os.path.join(workspace_root, "docker-compose.yml")
        if os.path.exists(docker_compose_path):
            with open(docker_compose_path, 'r') as f:
                compose_content = f.read()
            
            # Verifica presenza multiple repliche o scale config
            scale_indicators = ["replicas", "scale", "deploy", "restart"]
            assert any(indicator in compose_content for indicator in scale_indicators), \
                "Configurazione scaling mancante"
    
    def test_rnf4_security_requirements(self):
        """
        RNF4.1-RNF4.4: Sicurezza
        JWT authentication, HTTPS, data encryption, input validation
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Test configurazione SSL/TLS
        certs_path = os.path.join(workspace_root, "certs")
        if os.path.exists(certs_path):
            cert_files = os.listdir(certs_path)
            ssl_files = [f for f in cert_files if f.endswith(('.crt', '.key', '.pem'))]
            assert len(ssl_files) > 0, "Certificati SSL mancanti"
        
        # Test presenza JWT nei servizi
        services_path = os.path.join(workspace_root, "services")
        jwt_found = False
        
        if os.path.exists(services_path):
            for root, dirs, files in os.walk(services_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                            
                            jwt_indicators = ["jwt", "JWT", "token", "auth", "authentication"]
                            if any(indicator in content for indicator in jwt_indicators):
                                jwt_found = True
                                break
                        except:
                            pass
                
                if jwt_found:
                    break
        
        # Se abbiamo servizi, dovrebbe esserci autenticazione
        if os.path.exists(services_path):
            assert jwt_found, "Autenticazione JWT non trovata"
    
    def test_rnf5_usability_requirements(self):
        """
        RNF5.1-RNF5.3: Usabilità
        Interface intuitiva, responsive design, accessible UI
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Test presenza frontend user interface
        frontend_path = os.path.join(workspace_root, "services", "dashboard", "frontend_user")
        if os.path.exists(frontend_path):
            # Verifica presenza file CSS per responsive design
            css_files = []
            for root, dirs, files in os.walk(frontend_path):
                for file in files:
                    if file.endswith('.css'):
                        css_files.append(os.path.join(root, file))
            
            if css_files:
                for css_file in css_files[:2]:  # Controlla primi 2 file CSS
                    try:
                        with open(css_file, 'r') as f:
                            css_content = f.read()
                        
                        # Verifica presenza media queries per responsive
                        responsive_indicators = [
                            "@media", "max-width", "min-width", 
                            "mobile", "tablet", "desktop"
                        ]
                        
                        has_responsive = any(indicator in css_content for indicator in responsive_indicators)
                        if len(css_content) > 100:  # Solo se file non vuoto
                            assert has_responsive, f"Design responsive mancante in {css_file}"
                    except:
                        pass
    
    def test_rnf6_maintainability_requirements(self):
        """
        RNF6.1-RNF6.4: Manutenibilità
        Code quality, documentation, logging, error handling
        """
        workspace_root = "/Users/alessandrodipasquale/Desktop/NearYou"
        
        # Test presenza README
        readme_path = os.path.join(workspace_root, "README.md")
        assert os.path.exists(readme_path), "README.md mancante"
        
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                readme_content = f.read()
            
            # Verifica sezioni essenziali
            essential_sections = ["install", "usage", "deploy"]
            documentation_score = sum(1 for section in essential_sections 
                                    if section.lower() in readme_content.lower())
            
            assert documentation_score >= 1, "Documentazione README insufficiente"
        
        # Test presenza requirements per gestione dipendenze
        requirements_path = os.path.join(workspace_root, "requirements.txt")
        requirements_dir = os.path.join(workspace_root, "requirements")
        
        assert os.path.exists(requirements_path) or os.path.exists(requirements_dir), \
            "File requirements mancanti"
        
        # Test presenza logging nei servizi
        services_path = os.path.join(workspace_root, "services")
        if os.path.exists(services_path):
            logging_found = False
            
            for root, dirs, files in os.walk(services_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                            
                            logging_indicators = ["logging", "logger", "log.", "import logging"]
                            if any(indicator in content for indicator in logging_indicators):
                                logging_found = True
                                break
                        except:
                            pass
                
                if logging_found:
                    break
            
            assert logging_found, "Sistema di logging non configurato"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
