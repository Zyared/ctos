"""Безопасная отмена after-jobs в Tk и общие мелкие помощники отрисовки."""

from __future__ import annotations

import tkinter as tk


def after_cancel_safe(root: tk.Misc, job: str | None) -> None:
    if job is None:
        return
    try:
        root.after_cancel(job)
    except tk.TclError:
        pass


def draw_corner_frame(
    canvas: tk.Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    outline: str,
    fill: str = "",
    frame_width: int = 1,
    bracket_len: float = 14,
    bracket_width: int = 2,
    tags: tuple[str, ...] = (),
) -> int:
    """Панель-рамка с акцентными «уголками» на двух противоположных углах —
    тот же приём, что и в HUD-панелях главного меню (PROFILER/NETWORK MAP).
    Значения уже должны быть в экранных px (вызывающий код сам применяет vp.px).
    Возвращает id основного прямоугольника (как обычный create_rectangle).
    """
    rect = canvas.create_rectangle(
        x0, y0, x1, y1, outline=outline, width=frame_width, fill=fill, tags=tags,
    )
    canvas.create_line(x0, y0, x0 + bracket_len, y0, fill=outline, width=bracket_width, tags=tags)
    canvas.create_line(x0, y0, x0, y0 + bracket_len, fill=outline, width=bracket_width, tags=tags)
    canvas.create_line(x1, y1, x1 - bracket_len, y1, fill=outline, width=bracket_width, tags=tags)
    canvas.create_line(x1, y1, x1, y1 - bracket_len, fill=outline, width=bracket_width, tags=tags)
    return rect
