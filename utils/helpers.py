import asyncio
import re
from typing import Callable, Any

def markdown_to_html(text: str) -> str:
    """Converte un subset del markdown (**, *, #) in HTML per Telegram."""
    # Escape base per evitare che `<` o `>` scoccati casualmente rompano l'XML parser
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Headers trasformati in grassetto (rimuoviamo eventuali ** interni per non annidarli)
    def header_repl(match):
        content = match.group(2).replace('**', '').replace('*', '')
        return f"<b>{content}</b>"
    text = re.sub(r'^(#{1,6})\s+(.+)$', header_repl, text, flags=re.MULTILINE)
    
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    # Italic
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text, flags=re.DOTALL)
    return text

async def send_split_message(status_msg: Any, text: str, parse_mode: str = "Markdown", chunk_size: int = 4000):
    """
    Splits a long text into chunks. 
    The first chunk edits the status_msg.
    Subsequent chunks are sent as replies to the chat.
    """
    if parse_mode == "HTML_from_Markdown":
        text = markdown_to_html(text)
        parse_mode = "HTML"
        
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    if not chunks:
        return
        
    try:
        await status_msg.edit_text(chunks[0], parse_mode=parse_mode)
    except Exception:
        await status_msg.edit_text(chunks[0]) # Fallback senza parse_mode
        
    for chunk in chunks[1:]:
        try:
            await status_msg.answer(chunk, parse_mode=parse_mode)
        except Exception:
            await status_msg.answer(chunk)

async def invoke_with_backoff(graph: Any, input_data: Any, config: dict, status_msg: Any = None):
    """
    Invokes a LangGraph with exponential backoff se si verifica un Rate Limit (429).
    Aggiorna status_msg se fornito.
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
                    if status_msg:
                        try:
                            await status_msg.edit_text(f"⏳ <b>Attendi</b>, sto per elaborare...\n<i>(Il motore IA è saturo, nuovo tentativo tra {wait_time}s)</i>", parse_mode="HTML")
                        except Exception:
                            pass
                    await asyncio.sleep(wait_time)
                    continue
            raise e
