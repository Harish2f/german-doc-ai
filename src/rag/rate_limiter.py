import time
import asyncio
from collections import deque
from src.logger import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Track request timestamps in a Sliding window. If the limit
     is reached, wait until the oldest request falls outside
    the window before allowing the next request through.
    
    This prevents hitting Azure OpenAI's token-per-minute 
    and requests-per-minute limits.
    """

    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        name: str = "azure_openai",
    ):
        self.max_requests = max_requests
        self.window_seconds= window_seconds
        self.name = name
        self.requests: deque = deque()


    def _clean_old_requests(self)-> None:
        """Remove requests outside the current time window."""
        now = time.time()
        while self.requests and now - self.requests[0] >= self.window_seconds:
            self.requests.popleft()


    async def acquire(self)-> None:
        """Wait until a request slot is available.
        
        If under the limit, returns immediately.
        If at the limit, sleeps until the oldest request
        falls outside the window.
        """
        while True:
            self._clean_old_requests()

            if len(self.requests) < self.max_requests:
                self.requests.append(time.time())
                logger.debug(
                    "rate_limiter_acquired",
                    name=self.name,
                    current_requests = len(self.requests),
                    max_requests=self.max_requests,
                )
                return
            
            # At limit - calculate wait time
            oldest_request = self.requests[0]
            wait_time = self.window_seconds- (time.time() - oldest_request)

            logger.warning(
                "rate_limiter_waiting",
                name=self.name,
                wait_seconds = round(wait_time, 2),
                current_requests=len(self.requests),
            )
            await asyncio.sleep(max(0,wait_time))


# Global rate limiter instance shared across all requests
llm_rate_limiter = RateLimiter(
    max_requests = 60,
    window_seconds = 60,
    name="azure_openai",
)