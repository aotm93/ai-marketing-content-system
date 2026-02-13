"""
Unit tests for Research Cache

Tests three-tier cache functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.services.research.cache import ResearchCache
from src.models.content_intelligence import ResearchCacheEntry


class TestResearchCache:
    """Unit tests for ResearchCache"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.commit.return_value = None
        return db
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        redis = Mock()
        redis.get = Mock(return_value=None)
        redis.set = Mock(return_value=True)
        redis.delete = Mock(return_value=True)
        return redis
    
    @pytest.fixture
    def cache(self, mock_db, mock_redis):
        """Create a ResearchCache instance with mocked dependencies"""
        return ResearchCache(db=mock_db, redis_client=mock_redis)
    
    @pytest.mark.asyncio
    async def test_l1_memory_cache_hit(self, cache):
        """Test L1 memory cache returns data immediately"""
        # Arrange
        test_data = {"key": "value", "nested": {"data": 123}}
        await cache.set("test_key", test_data)
        
        # Act
        result = await cache.get("test_key")
        
        # Assert
        assert result == test_data
        stats = cache.get_stats()
        assert stats["memory_hits"] == 1
    
    @pytest.mark.asyncio
    async def test_l1_cache_expiration(self, cache):
        """Test expired L1 entries are removed"""
        # Arrange - Set with very short TTL
        cache.memory_ttl = 0  # Immediate expiration
        await cache.set("expired_key", {"data": "test"})
        
        # Act
        result = await cache.get("expired_key")
        
        # Assert
        assert result is None
        assert "expired_key" not in cache.memory_cache
    
    @pytest.mark.asyncio
    async def test_l2_redis_cache_hit(self, cache, mock_redis):
        """Test L2 Redis cache fallback"""
        # Arrange
        test_data = {"source": "redis", "value": 456}
        mock_redis.get.return_value = json.dumps(test_data)
        
        # Act
        result = await cache.get("redis_key")
        
        # Assert
        assert result == test_data
        stats = cache.get_stats()
        assert stats["redis_hits"] == 1
        # Should promote to L1
        assert "redis_key" in cache.memory_cache
    
    @pytest.mark.asyncio
    async def test_l3_database_cache_hit(self, cache, mock_db):
        """Test L3 database cache fallback"""
        # Arrange
        test_data = {"source": "database", "value": 789}
        cache_entry = Mock()
        cache_entry.data = json.dumps(test_data)
        cache_entry.expires_at = datetime.now() + timedelta(days=1)
        cache_entry.access_count = 0
        cache_entry.last_accessed_at = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry
        
        # Act
        result = await cache.get("db_key")
        
        # Assert
        assert result == test_data
        stats = cache.get_stats()
        assert stats["db_hits"] == 1
        # Should update access stats
        assert cache_entry.access_count == 1
    
    @pytest.mark.asyncio
    async def test_complete_cache_miss(self, cache):
        """Test complete miss when no cache level has data"""
        # Act
        result = await cache.get("nonexistent")
        
        # Assert
        assert result is None
        stats = cache.get_stats()
        assert stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_set_populates_all_levels(self, cache, mock_db, mock_redis):
        """Test that set populates L1, L2, and L3"""
        # Arrange
        test_data = {"test": "data"}
        
        # Act
        await cache.set("multi_key", test_data)
        
        # Assert
        # L1
        assert "multi_key" in cache.memory_cache
        # L2
        mock_redis.set.assert_called_once()
        # L3
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_removes_all_levels(self, cache, mock_db, mock_redis):
        """Test that delete removes from all levels"""
        # Arrange
        cache.memory_cache["del_key"] = ({"data": "test"}, datetime.now())
        
        # Act
        await cache.delete("del_key")
        
        # Assert
        assert "del_key" not in cache.memory_cache
        mock_redis.delete.assert_called_once_with("del_key")
        mock_db.query.return_value.filter_by.return_value.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_entries(self, cache, mock_db):
        """Test cleanup removes expired entries"""
        # Arrange
        now = datetime.now()
        cache.memory_cache["fresh"] = ({"data": 1}, now + timedelta(hours=1))
        cache.memory_cache["expired"] = ({"data": 2}, now - timedelta(hours=1))
        cache.memory_cache["also_expired"] = ({"data": 3}, now - timedelta(minutes=5))
        
        expired_db_entry = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 5
        
        # Act
        cleaned = await cache.cleanup_expired(db=mock_db)
        
        # Assert
        assert "fresh" in cache.memory_cache
        assert "expired" not in cache.memory_cache
        assert "also_expired" not in cache.memory_cache
        assert cleaned >= 2  # At least the 2 memory entries
    
    @pytest.mark.asyncio
    async def test_cache_stats_accuracy(self, cache):
        """Test that stats accurately track hits and misses"""
        # Arrange - Create known state
        await cache.set("key1", "data1")
        await cache.set("key2", "data2")
        
        # Act - Generate known hit/miss pattern
        await cache.get("key1")  # Hit
        await cache.get("key1")  # Hit
        await cache.get("key2")  # Hit
        await cache.get("missing1")  # Miss
        await cache.get("missing2")  # Miss
        
        # Assert
        stats = cache.get_stats()
        assert stats["memory_hits"] == 3
        assert stats["misses"] == 2
        assert stats["total_requests"] == 5
        assert abs(stats["hit_rate"] - 0.6) < 0.01  # 3/5 = 0.6
    
    @pytest.mark.asyncio
    async def test_hit_rate_calculations(self, cache):
        """Test individual hit rate calculations"""
        # Arrange
        for i in range(10):
            await cache.set(f"key_{i}", f"data_{i}")
        
        # Generate hits at different levels
        for i in range(10):
            await cache.get(f"key_{i}")  # Memory hits
        
        for _ in range(5):
            await cache.get("nonexistent")  # Misses
        
        # Act
        memory_rate = await cache.get_memory_hit_rate()
        redis_rate = await cache.get_redis_hit_rate()
        db_rate = await cache.get_db_hit_rate()
        
        # Assert
        assert abs(memory_rate - (10/15)) < 0.01
        assert redis_rate == 0.0  # No Redis hits in this test
        assert db_rate == 0.0  # No DB hits in this test
    
    @pytest.mark.asyncio
    async def test_api_calls_saved_counter(self, cache):
        """Test that API calls saved counter increments on hits"""
        # Arrange
        await cache.set("key", "data")
        
        # Act - Each hit should increment saved counter
        await cache.get("key")
        await cache.get("key")
        await cache.get("key")
        
        # Assert
        saved = await cache.get_api_calls_saved()
        assert saved == 3
    
    @pytest.mark.asyncio
    async def test_database_persistence(self, cache, mock_db):
        """Test that data persists to database correctly"""
        # Arrange
        test_data = {"research": "results", "topics": ["a", "b", "c"]}
        
        # Act
        await cache.set("persist_key", test_data, ttl=86400)
        
        # Assert
        mock_db.add.assert_called_once()
        added_entry = mock_db.add.call_args[0][0]
        assert isinstance(added_entry, ResearchCacheEntry)
        assert added_entry.cache_key == "persist_key"
        assert json.loads(added_entry.data) == test_data
        assert added_entry.expires_at > datetime.now()
    
    @pytest.mark.asyncio
    async def test_l3_to_l2_promotion(self, cache, mock_db, mock_redis):
        """Test that L3 hits promote to L2"""
        # Arrange
        test_data = {"promoted": True}
        cache_entry = Mock()
        cache_entry.data = json.dumps(test_data)
        cache_entry.expires_at = datetime.now() + timedelta(days=1)
        cache_entry.access_count = 0
        cache_entry.last_accessed_at = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = cache_entry
        
        # Act
        result = await cache.get("promote_key")
        
        # Assert
        assert result == test_data
        # Should set in Redis
        mock_redis.set.assert_called()
    
    def test_cache_initialization(self, mock_db):
        """Test cache initializes with correct defaults"""
        cache = ResearchCache(db=mock_db)
        
        assert cache.memory_ttl == 3600
        assert cache.redis_ttl == 86400
        assert cache.db_ttl == 604800
        assert cache.memory_cache == {}
        assert cache.stats["memory_hits"] == 0
