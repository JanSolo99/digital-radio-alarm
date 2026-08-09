"""Local alarm list - persisted the same way favorites are, so the project
stays on one storage pattern instead of introducing a database.
"""

import json
import uuid
from pathlib import Path

ALARMS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "alarms.json"

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def load_alarms():
    if not ALARMS_PATH.exists():
        return []
    with ALARMS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_alarms(alarms):
    with ALARMS_PATH.open("w", encoding="utf-8") as f:
        json.dump(alarms, f, indent=2)
        f.write("\n")


def add_alarm(time, station_id, days=None, enabled=True, volume=60):
    """time is 'HH:MM' 24-hour. days is a subset of DAYS; empty/None means every day.
    volume is the target the fade-in ramps up to, 0-100 - per-alarm so a weekday
    wake-up can be louder than a weekend one.
    """
    alarms = load_alarms()
    alarms.append(
        {
            "id": str(uuid.uuid4()),
            "time": time,
            "station_id": station_id,
            "enabled": enabled,
            "days": list(days) if days else [],
            "volume": volume,
        }
    )
    save_alarms(alarms)
    return alarms


def update_alarm(alarm_id, **fields):
    alarms = load_alarms()
    for alarm in alarms:
        if alarm["id"] == alarm_id:
            alarm.update(fields)
            break
    save_alarms(alarms)
    return alarms


def remove_alarm(alarm_id):
    alarms = [a for a in load_alarms() if a["id"] != alarm_id]
    save_alarms(alarms)
    return alarms
