# scheduler/logic.py
from collections import Counter
from typing import List, Tuple

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def compute_best_overlaps(
    participants: List[int],
    availability_rows: List[Tuple[int, int, int, int]],
    top_n: int = 10,
) -> List[Tuple[int, int, int]]:
    """
    participants: [user_id...]
    availability_rows: [(user_id, day_index, start_minutes, duration_minutes), ...]

    Returns [(day_index, start_minutes, count)] sorted by count desc, then day/time.
    """
    pset = set(participants)

    keys = [
        (day_idx, start_min)
        for (uid, day_idx, start_min, _dur) in availability_rows
        if uid in pset
    ]

    counts = Counter(keys)
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))
    return [(day, start, cnt) for ((day, start), cnt) in ranked[:top_n]]