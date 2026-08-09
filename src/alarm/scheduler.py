"""Pure scheduling logic - given the current alarm list and a timestamp,
figure out what should happen. No I/O, no hardware, so it's easy to test
without a Pi attached.
"""

from datetime import timedelta

_DAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

SNOOZE_MINUTES = 9


def _matches_day(alarm, when):
    days = alarm.get("days") or []
    return not days or _DAY_CODES[when.weekday()] in days


def find_due_alarm(alarms, now):
    """First enabled alarm whose time matches `now` to the minute, or None.

    Call this at most once per minute - it doesn't track whether it already
    fired, so calling it repeatedly within the same minute returns the same
    alarm every time.
    """
    current = now.strftime("%H:%M")
    for alarm in alarms:
        if alarm.get("enabled") and alarm["time"] == current and _matches_day(alarm, now):
            return alarm
    return None


def next_alarm_time(alarms, now):
    """Datetime of the next enabled alarm's next occurrence, or None if no
    alarms are enabled. Useful for a "next alarm in 7h 40m" display line.
    """
    candidates = []
    for alarm in alarms:
        if not alarm.get("enabled"):
            continue
        hour, minute = (int(part) for part in alarm["time"].split(":"))
        for days_ahead in range(8):
            candidate = (now + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if candidate <= now:
                continue
            if _matches_day(alarm, candidate):
                candidates.append(candidate)
                break
    return min(candidates) if candidates else None


def snooze_until(now, minutes=SNOOZE_MINUTES):
    return now + timedelta(minutes=minutes)
