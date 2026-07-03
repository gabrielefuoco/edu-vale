from ics import Calendar, Event
from datetime import datetime

def generate_ics_file(date_str: str, start_time: str, end_time: str, user_name: str, location: str, filename="evento.ics") -> str:
    c = Calendar()
    e = Event()
    e.name = f"Sessione Edu: {user_name}"
    e.begin = f"{date_str} {start_time}:00"
    e.end = f"{date_str} {end_time}:00"
    e.location = location or ""
    c.events.add(e)
    
    with open(filename, 'w') as f:
        f.writelines(c.serialize_iter())
    return filename
