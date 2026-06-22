import redis
from backend.config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=6379,
    decode_responses=True
)