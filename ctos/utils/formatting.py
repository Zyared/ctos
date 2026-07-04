"""Форматирование чисел для UI (избегаем артефактов float)."""

from __future__ import annotations


def format_speed_kbps(value: float | int) -> str:
    """Отображение скорости без длинных хвостов float."""
    v = float(value)
    if v <= 0:
        return "0 KB/s"
    if abs(v - round(v)) < 1e-6:
        return f"{int(round(v))} KB/s"
    return f"{round(v, 1):.1f} KB/s"
