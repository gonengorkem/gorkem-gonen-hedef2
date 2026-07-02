import os
import json
import redis
from typing import Optional, Any

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

class RedisCacheService:
    def __init__(self):
        self.is_redis_enabled = False
        self.client = None
        
        try:
            # Create a redis client with short connection timeout (2 seconds)
            self.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True # Returns string instead of bytes
            )
            # Test connection
            self.client.ping()
            self.is_redis_enabled = True
            print(f"[RedisCache] Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            print(f"[RedisCache] Redis connection failed: {str(e)}. Caching will be disabled.")
            self.is_redis_enabled = False
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from Redis cache. Returns None if not found or Redis is disabled.
        """
        if not self.is_redis_enabled or not self.client:
            return None
            
        try:
            val = self.client.get(key)
            if val:
                # Try parsing as JSON, fallback to raw string if it's not JSON
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return val
            return None
        except Exception as e:
            print(f"[RedisCache] Error retrieving key '{key}': {str(e)}")
            return None

    def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """
        Stores a value in Redis cache. Automatically serializes dicts/lists to JSON.
        """
        if not self.is_redis_enabled or not self.client:
            return False
            
        try:
            if isinstance(value, (dict, list)):
                serialized_val = json.dumps(value)
            else:
                serialized_val = str(value)
                
            self.client.set(key, serialized_val, ex=expire_seconds)
            return True
        except Exception as e:
            print(f"[RedisCache] Error setting key '{key}': {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Removes a key from cache.
        """
        if not self.is_redis_enabled or not self.client:
            return False
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"[RedisCache] Error deleting key '{key}': {str(e)}")
            return False

    def clear_prefix(self, prefix: str) -> bool:
        """
        Deletes all keys in Redis matching the given prefix.
        """
        if not self.is_redis_enabled or not self.client:
            return False
        try:
            keys = self.client.keys(f"{prefix}*")
            if keys:
                self.client.delete(*keys)
                print(f"[RedisCache] Cleared cache keys starting with prefix: {prefix}")
            return True
        except Exception as e:
            print(f"[RedisCache] Error clearing prefix '{prefix}': {str(e)}")
            return False


# Export a singleton instance
redis_cache = RedisCacheService()
