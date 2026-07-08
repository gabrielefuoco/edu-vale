import asyncio
from typing import Callable, Any

async def invoke_with_backoff(graph: Any, input_data: Any, config: dict, bot_message_func: Callable):
    """
    Invokes a LangGraph with exponential backoff if a Rate Limit (429) occurs.
    """
    max_retries = 4
    for attempt in range(max_retries):
        try:
            return await graph.ainvoke(input_data, config=config)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                if attempt < max_retries - 1:
                    wait_time = 3 * (2 ** attempt)  # 3, 6, 12 secondi
                    try:
                        await bot_message_func(f"⏳ <b>Attendi</b>, sto per risponderti...\n<i>(Il motore IA è temporaneamente saturo, nuovo tentativo tra {wait_time}s)</i>")
                    except Exception:
                        pass
                    await asyncio.sleep(wait_time)
                    continue
            raise e
