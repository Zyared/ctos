"""Точка входа GUI."""

from __future__ import annotations

import tkinter as tk

from ctos.ui.application import CtOSApplication


def run_ctos() -> None:
    root = tk.Tk()
    app = CtOSApplication(root)
    app.start_music()
    root.mainloop()
