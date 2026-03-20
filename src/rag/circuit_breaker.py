import time
from enum import Enum
from src.logger import get_logger

logger = get_logger(__name__)

class CircuitState(Enum):
   CLOSED = "closed"
   OPEN = "open"
   HALF_OPEN = "half_open"


class CircuitBreaker:
   """Circuit breaker for Azure OpenAI calls.
   
   Tracks consecutive failures and open the circuit after
   reaching the threshold - preventing cascading failures
   when Azure OpenAI is slow or unavailable.

   States:
    CLOSED: Normal operation, requests pass through.
    OPEN: Failing fast, requests rejected immediately.
    HALF_OPEN: Testing recovery, one request allowed through.
   """
   def __init__(
      self,
      failure_threshold: int = 5,
      recovery_timeout: int = 60,
      name: str = "azure_openai" ,  
   ):
      self.failure_threshold = failure_threshold
      self.recovery_timeout = recovery_timeout
      self.name = name
      self.state = CircuitState.CLOSED
      self.failure_count = 0
      self.last_failure_time: float | None = None

    
   def _should_attempt_reset(self) -> bool:
    """Check if enough time has passed to try recovery."""
    if self.last_failure_time is None:
       return False
    return time.time() - self.last_failure_time >= self.recovery_timeout
   

   def call_succeeded(self) -> None:
      """Record a successful call - reset failure count."""
      self.failure_count = 0
      self.state = CircuitState.CLOSED
      logger.info("circuit_breaker_closed", name=self.name)


   def call_failed(self) -> None:
      """Record a failed call - increment counter and open if threshold reached."""
      self.failure_count += 1
      self.last_failure_time = time.time()

      if self.failure_count >= self.failure_threshold:
         self.state = CircuitState.OPEN
         logger.warning(
            "circuit_breaker_opened",
            name = self.name,
            failure_count = self.failure_count,
         )


   def can_attempt(self)-> bool:
      """check if a request should be allowed throgh.
      
      Returns:
         True if request should proceed, False if it should be rejected.
      """
      if self.state == CircuitState.CLOSED:
         return True
      
      if self.state == CircuitState.OPEN:
         if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            logger.info("circuit_breaker_half_open", name=self.name)
            return True
         return False
      
      # Half Open - allow one test request
      return True

# Global circuit breaker instance shared across all requests
llm_circuit_breaker= CircuitBreaker(
   failure_threshold = 5,
   recovery_timeout = 60,
   name = "azure_openai",
)