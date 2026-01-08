# Helper module to process time

def to_minutes(hour, minute=0, ampm=None):
    hour = int(hour)
    minute = int(minute or 0)

    if ampm:
        ampm = ampm.lower()
        if ampm == "am":
            hour = 0 if hour == 12 else hour
        elif ampm == "pm":
            hour = 12 if hour == 12 else hour + 12
    else:
        # no am/pm provided
        # if hour >= 13, assume 24-hour
        if hour > 23:
            raise ValueError("Invalid hour")

    total = hour * 60 + minute
    return total

def minutes_to_label(minutes: int) -> str:
    minutes = int(minutes)
    hour = int(minutes // 60)
    minute = int(minutes % 60)
    ampm = "am" if hour < 12 else "pm"
    hour = hour % 12
    hour = 12 if hour == 0 else hour
    return f"{hour}:{minute:02d}{ampm}"