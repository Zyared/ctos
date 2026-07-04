"""
Реестр модулей (OCP): новый модуль добавляется сюда и в graph_nodes в UI,
без изменения логики клика по узлам.
"""

from __future__ import annotations

from typing import Callable

import tkinter as tk

from ctos.contracts import ExploitModule, OnExitCallback

from ctos.modules.bruteforce import BruteforceModule
from ctos.modules.data_exfil import DataExfilModule
from ctos.modules.network_sniffer import NetworkSnifferModule
from ctos.modules.placeholder_module import PlaceholderModule
from ctos.modules.zero_day import ZeroDownModule

Factory = Callable[[tk.Canvas, tk.Tk, OnExitCallback], ExploitModule]


def _make_bruteforce(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = BruteforceModule(canvas, root, on_exit)
    module.start()
    return module


def _make_sniffer(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = NetworkSnifferModule(canvas, root, on_exit)
    module.start()
    return module


def _make_exfil(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = DataExfilModule(canvas, root, on_exit)
    module.start()
    return module


def _make_zero_day(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = ZeroDownModule(canvas, root, on_exit)
    module.start()
    return module


def _make_social_eng(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = PlaceholderModule(
        canvas,
        root,
        on_exit,
        "SOCIAL ENGINEERING",
        "Модуль в разработке.\n\n"
        "Социальная инженерия (учебная тема):\n"
        "• фишинг и претекстинг\n"
        "• манипуляция и имитация доверия\n"
        "• сценарии для awareness-тренингов\n\n"
        "Здесь появится интерактивная симуляция.",
    )
    module.start()
    return module


def _make_phishing(canvas: tk.Canvas, root: tk.Tk, on_exit: OnExitCallback) -> ExploitModule:
    module = PlaceholderModule(
        canvas,
        root,
        on_exit,
        "PHISHING LAB",
        "Модуль в разработке.\n\n"
        "Фишинг (учебная симуляция):\n"
        "• поддельные страницы и письма\n"
        "• разбор признаков атаки\n"
        "• безопасные drill-сценарии\n\n"
        "Контент будет добавлен в следующих версиях.",
    )
    module.start()
    return module


DEFAULT_MODULE_FACTORIES: dict[str, Factory | None] = {
    "BRUTEFORCE": _make_bruteforce,
    "NETWORK SNIFFER": _make_sniffer,
    "DATA EXFIL": _make_exfil,
    "ZERO-DAY": _make_zero_day,
    "SOCIAL ENG.": _make_social_eng,
    "PHISHING": _make_phishing,
}
