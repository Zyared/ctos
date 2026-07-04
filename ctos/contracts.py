"""Абстракции модулей CtOS (DIP / ISP)."""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

import tkinter as tk

OnExitCallback = Callable[[], None]


@runtime_checkable
class ExploitModule(Protocol):
    """Модуль сценария: после создания вызывается start() (кроме legacy-исключений — см. фабрику)."""

    def start(self) -> None: ...


ExploitFactory = Callable[[tk.Canvas, tk.Tk, OnExitCallback], ExploitModule]
