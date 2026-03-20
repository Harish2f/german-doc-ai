import pytest
from src.rag.rate_limiter import RateLimiter

@pytest.mark.asyncio
async def test_acquire():
    rl = RateLimiter()
    assert len(rl.requests) == 0

@pytest.mark.asyncio
async def test_acquire_calls():
    rl = RateLimiter()
    for _ in range(10):
       await rl.acquire()
    assert len(rl.requests) == 10

