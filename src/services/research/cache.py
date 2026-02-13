"""
Research Cache

Three-tier caching system for research results.
"""

import logging
import json
import hashlib
from typing import Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class ResearchCache:
    """
    Three-tier cache: Memory -> Redis -> Database
    
    L1: Memory (1 hour TTL)
    L2: Redis (24 hour TTL)
    L3: Database (7 day TTL)
    """
    
    def __init__(self, db: Optional[Session] = None, redis_client=None):
        self.memory_cache = {}  # {key: (data, expiry)}
        self.memory_ttl = 3600  # 1 hour
        self.redis_ttl = 86400  # 24 hours
        self.db_ttl = 604800    # 7 days
        self._db = db
        self._redis = redis_client
        self.stats = {
            'memory_hits': 0,
            'redis_hits': 0,
            'db_hits': 0,
            'misses': 0,
            'api_calls_saved': 0
        }
        logger.info("ResearchCache initialized")
    
    def _get_db(self) -> Optional[Session]:
        """Get database session"""
        return self._db
    
    async def get(self, key: str) -> Optional[Any]:
        """Get data from cache with L1 -> L2 -> L3 fallback"""
        # L1: Memory cache
        if key in self.memory_cache:
            data, expiry = self.memory_cache[key]
            if datetime.now() < expiry:
                self.stats['memory_hits'] += 1
                self.stats['api_calls_saved'] += 1
                logger.debug(f"L1 cache hit for {key}")
                return data
            else:
                # Expired
                del self.memory_cache[key]
        
        # L2: Redis
        if self._redis:
            try:
                redis_data = await self._redis.get(key)
                if redis_data:
                    data = json.loads(redis_data)
                    # Promote to L1
                    expiry = datetime.now() + timedelta(seconds=self.memory_ttl)
                    self.memory_cache[key] = (data, expiry)
                    self.stats['redis_hits'] += 1
                    self.stats['api_calls_saved'] += 1
                    logger.debug(f"L2 cache hit for {key}")
                    return data
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # L3: Database
        db = self._get_db()
        if db:
            try:
                from src.models.content_intelligence import ResearchCacheEntry
                db_entry = db.query(ResearchCacheEntry).filter(
                    and_(
                        ResearchCacheEntry.cache_key == key,
                        ResearchCacheEntry.expires_at > datetime.now()
                    )
                ).first()
                
                if db_entry:
                    data = json.loads(db_entry.data)
                    # Promote to L1
                    expiry = datetime.now() + timedelta(seconds=self.memory_ttl)
                    self.memory_cache[key] = (data, expiry)
                    # Promote to L2 if Redis available
                    if self._redis:
                        try:
                            await self._redis.set(key, db_entry.data, ex=self.redis_ttl)
                        except Exception as e:
                            logger.error(f"Redis promote error: {e}")
                    # Update access stats
                    db_entry.access_count += 1
                    db_entry.last_accessed_at = datetime.now()
                    db.commit()
                    
                    self.stats['db_hits'] += 1
                    self.stats['api_calls_saved'] += 1
                    logger.debug(f"L3 cache hit for {key}")
                    return data
            except Exception as e:
                logger.error(f"Database get error: {e}")
        
        self.stats['misses'] += 1
        return None
    
    async def set(self, key: str, data: Any, ttl: int = 86400) -> bool:
        """Set data in all cache levels"""
        try:
            # Serialize data
            serialized_data = json.dumps(data, default=str)
            
            # L1: Memory
            expiry = datetime.now() + timedelta(seconds=min(ttl, self.memory_ttl))
            self.memory_cache[key] = (data, expiry)
            
            # L2: Redis
            if self._redis:
                try:
                    await self._redis.set(key, serialized_data, ex=min(ttl, self.redis_ttl))
                except Exception as e:
                    logger.error(f"Redis set error: {e}")
            
            # L3: Database
            db = self._get_db()
            if db:
                try:
                    from src.models.content_intelligence import ResearchCacheEntry
                    
                    # Check if entry exists
                    existing = db.query(ResearchCacheEntry).filter_by(cache_key=key).first()
                    
                    expires_at = datetime.now() + timedelta(seconds=min(ttl, self.db_ttl))
                    context_hash = hashlib.md5(serialized_data.encode()).hexdigest()
                    
                    if existing:
                        existing.data = serialized_data
                        existing.expires_at = expires_at
                        existing.context_hash = context_hash
                    else:
                        entry = ResearchCacheEntry(
                            cache_key=key,
                            data=serialized_data,
                            context_hash=context_hash,
                            expires_at=expires_at,
                            access_count=0
                        )
                        db.add(entry)
                    
                    db.commit()
                except Exception as e:
                    logger.error(f"Database set error: {e}")
                    db.rollback()
            
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete data from all cache levels"""
        try:
            # L1
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # L2: Redis
            if self._redis:
                try:
                    await self._redis.delete(key)
                except Exception as e:
                    logger.error(f"Redis delete error: {e}")
            
            # L3: Database
            db = self._get_db()
            if db:
                try:
                    from src.models.content_intelligence import ResearchCacheEntry
                    db.query(ResearchCacheEntry).filter_by(cache_key=key).delete()
                    db.commit()
                except Exception as e:
                    logger.error(f"Database delete error: {e}")
                    db.rollback()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting cache: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_hits = self.stats['memory_hits'] + self.stats['redis_hits'] + self.stats['db_hits']
        total_requests = total_hits + self.stats['misses']
        
        hit_rate = total_hits / total_requests if total_requests > 0 else 0
        
        return {
            'memory_hits': self.stats['memory_hits'],
            'redis_hits': self.stats['redis_hits'],
            'db_hits': self.stats['db_hits'],
            'misses': self.stats['misses'],
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'api_calls_saved': self.stats['api_calls_saved'],
            'memory_cache_size': len(self.memory_cache)
        }
    
    async def get_memory_hit_rate(self) -> float:
        """Get L1 memory cache hit rate"""
        total = self.stats['memory_hits'] + self.stats['redis_hits'] + self.stats['db_hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return self.stats['memory_hits'] / total
    
    async def get_redis_hit_rate(self) -> float:
        """Get L2 Redis cache hit rate"""
        total = self.stats['memory_hits'] + self.stats['redis_hits'] + self.stats['db_hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return self.stats['redis_hits'] / total
    
    async def get_db_hit_rate(self) -> float:
        """Get L3 database cache hit rate"""
        total = self.stats['memory_hits'] + self.stats['redis_hits'] + self.stats['db_hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return self.stats['db_hits'] / total
    
    async def get_api_calls_saved(self) -> int:
        """Get number of API calls saved by caching"""
        return self.stats['api_calls_saved']
    
    async def get_total_topics(self, db: Session = None) -> int:
        """Get total number of cached topics from database"""
        if db is None:
            db = self._get_db()
        if db:
            try:
                from src.models.content_intelligence import ResearchCacheEntry
                return db.query(ResearchCacheEntry).count()
            except Exception as e:
                logger.error(f"Error counting cache entries: {e}")
        return 0
    
    async def cleanup_expired(self, db: Session = None) -> int:
        """Clean up expired entries from all cache levels"""
        cleaned = 0
        
        # L1: Memory
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self.memory_cache.items()
            if now > expiry
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            cleaned += 1
        
        # L3: Database
        if db is None:
            db = self._get_db()
        if db:
            try:
                from src.models.content_intelligence import ResearchCacheEntry
                result = db.query(ResearchCacheEntry).filter(
                    ResearchCacheEntry.expires_at < datetime.now()
                ).delete()
                db.commit()
                cleaned += result
                logger.info(f"Cleaned {result} expired entries from database cache")
            except Exception as e:
                logger.error(f"Error cleaning database cache: {e}")
                db.rollback()
        
        return cleaned
