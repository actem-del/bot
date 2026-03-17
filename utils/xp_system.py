from __future__ import annotations


def xp_for_next_level(level: int, curve: int = 100) -> int:
    return curve * (level**2)


def level_from_xp(total_xp: int, curve: int = 100) -> int:
    level = 1
    while total_xp >= xp_for_next_level(level, curve):
        level += 1
    return level


def progress_in_level(total_xp: int, curve: int = 100) -> tuple[int, int]:
    level = level_from_xp(total_xp, curve)
    prev_threshold = xp_for_next_level(level - 1, curve) if level > 1 else 0
    next_threshold = xp_for_next_level(level, curve)
    return total_xp - prev_threshold, next_threshold - prev_threshold
