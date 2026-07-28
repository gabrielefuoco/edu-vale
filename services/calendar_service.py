from ics import Calendar, Event
from datetime import datetime

def generate_ics_file(date_str: str, start_time: str, end_time: str, user_name: str, location: str, filename="evento.ics") -> str:
    c = Calendar()
    e = Event()
    e.name = f"Sessione Edu: {user_name}"
    try:
        e.begin = f"{date_str} {start_time or '00:00'}:00"
        e.end = f"{date_str} {end_time or '23:59'}:00"
    except Exception:
        e.make_all_day()
    e.location = location or ""
    c.events.add(e)
    
    with open(filename, 'w') as f:
        f.writelines(c.serialize_iter())
    return filename
