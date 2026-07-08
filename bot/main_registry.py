import asyncio

AGENT_REGISTRY = {}
_processing_locks: dict[str, asyncio.Lock] = {}
