import time
from collections import defaultdict

class InMemoryRateLimiter:
    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 100):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> tuple[bool, str | None]:
        now = time.time()
        # Pulizia timestamps > 1 ora
        self._timestamps[user_id] = [
            t for t in self._timestamps[user_id] if now - t < 3600
        ]
        ts = self._timestamps[user_id]
        
        last_minute = sum(1 for t in ts if now - t < 60)
        if last_minute >= self.max_per_minute:
            return False, "⏳ Troppi messaggi. Riprova tra un minuto."
            
        if len(ts) >= self.max_per_hour:
            return False, "⏳ Hai raggiunto il limite orario. Fai una pausa."
            
        ts.append(now)
        return True, None
