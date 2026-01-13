import math
import time
import asyncio
from typing import Dict

from ...exceptions.exceptions import RateLimitError
from ...identification import RustServer

class TokenBucket:
    def __init__(self, current: float, maximum: float, refresh_rate: float, refresh_amount: float) -> None:
        self.current = current
        self.max = maximum
        self.refresh_rate = refresh_rate
        self.refresh_amount = refresh_amount
        self.last_update = time.time()
        self.refresh_per_second = self.refresh_amount / self.refresh_rate
    
    def can_consume(self, amount) -> bool:
        return (self.current - amount) >= 0
    
    def consume(self, amount: int = 1) -> None:
        self.current -= amount

    def refresh(self) -> None:
        time_now = time.time()
        time_delta = time_now - self.last_update
        self.last_update = time_now
        self.current = min(self.current + time_delta * self.refresh_per_second, self.max)


class RateLimiter:
    SERVER_LIMIT = 50
    SERVER_REFRESH_AMOUNT = 15
    REFRESH_RATE = 1 # 1 sec for both
    SOCKET_LIMIT = 25
    SOCKET_REFRESH_AMOUNT = 3

    @classmethod
    def default(cls) -> "RateLimiter":
        """
        Returns a default rate limiter with 3 tokens per second
        """
        return cls()
    
    def __init__(self) -> None:
        self.socket_bucket: Dict[RustServer, TokenBucket] = {}
        self.server_bucket: Dict[RustServer, TokenBucket] = {}
        self.lock = asyncio.Lock()

    
    def add_socket(self, server_details: RustServer) -> None:
        self.socket_bucket[server_details] = TokenBucket(self.SOCKET_LIMIT, self.SOCKET_LIMIT, self.REFRESH_RATE, self.SOCKET_REFRESH_AMOUNT)
        self.server_bucket[server_details] = TokenBucket(self.SERVER_LIMIT, self.SERVER_LIMIT, self.REFRESH_RATE, self.SERVER_REFRESH_AMOUNT)


    async def can_consume(self, server_details: RustServer, amount: int = 1) -> bool:
        async with self.lock:
            for bucket in [
                self.socket_bucket.get(server_details), 
                self.server_bucket.get(server_details)
            ]:
                bucket.refresh()
                if not bucket.can_consume(amount):
                    return False
            
            return True
        
    async def consume(self, server_details: RustServer, amount: int = 1) -> None:
        async with self.lock:
            for bucket in [
                self.socket_bucket.get(server_details), self.server_bucket.get(server_details)
            ]:
                bucket.refresh()
                if not bucket.can_consume(amount):
                    raise RateLimitError("Not enough tokens")
            
            for bucket in [
                self.socket_bucket.get(server_details), self.server_bucket.get(server_details)
            ]:
                bucket.consume(amount)

    async def get_estimated_delay_time(self, server_details: RustServer, event_cost: int) -> float:
        async with self.lock:
            delay = 0
            for bucket in [
                self.socket_bucket.get(server_details), self.server_bucket.get(server_details)
            ]:
                val = math.ceil(((event_cost - bucket.current) / bucket.refresh_per_second + 0.1) *100 ) / 100 

                if val > delay:
                    delay = val
        
        return delay
    
    async def remove(self, server_details: RustServer) -> None:

        async with self.lock:
            del self.socket_bucket[server_details]
            del self.server_bucket[server_details]