"""
Единый масштаб UI: эталон 1920×1080 (Full HD).
На других разрешениях min(w/W, h/H) даёт одинаковую «плотность» картинки.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

BASE_W = 1920
BASE_H = 1080


@dataclass(frozen=True)
class Viewport:
    """Размеры окна/канвы и коэффициент относительно эталона."""

    w: int
    h: int
    scale: float

    @classmethod
    def from_canvas(cls, canvas: tk.Canvas, root: tk.Tk | None = None) -> "Viewport":
        if root is not None:
            root.update_idletasks()
        cw = max(int(canvas.winfo_width()), 1)
        ch = max(int(canvas.winfo_height()), 1)
        # До первого layout winfo_* часто даёт 1×1 — берём экран
        if cw < 120 or ch < 120:
            cw = max(int(canvas.winfo_screenwidth()), 1)
            ch = max(int(canvas.winfo_screenheight()), 1)
        scale = min(cw / BASE_W, ch / BASE_H)
        return cls(w=cw, h=ch, scale=scale)

    def px(self, n: float) -> int:
        """Координаты и расстояния в «дизайн-пикселях» 1920×1080 → экран."""
        return int(round(n * self.scale))

    def px_nonneg(self, n: float) -> int:
        v = int(round(n * self.scale))
        return v if v >= 0 else 0

    def pt(self, n: int) -> int:
        """Размер шрифта (не меньше 6 px)."""
        return max(6, int(round(n * self.scale)))

    def wid(self, n: float) -> int:
        """Толщина линии (минимум 1)."""
        return max(1, int(round(n * self.scale)))

    def consolas(self, size: int, bold: bool = False) -> tuple:
        p = self.pt(size)
        if bold:
            return ("Consolas", p, "bold")
        return ("Consolas", p)

    def arial_black(self, size: int) -> tuple:
        return ("Arial Black", self.pt(size))

    def dash(self, a: float, b: float) -> tuple[int, int]:
        return (self.wid(a), self.wid(b))
