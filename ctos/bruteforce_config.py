"""
Данные и тексты модуля BRUTEFORCE (только симуляция, учебный контент).
"""

from __future__ import annotations

# Сети для сканера (вымышленные)
NETWORKS: list[dict] = [
    {"ssid": "TP-LINK_2A3F", "signal": -66, "target": False},
    {"ssid": "SCHOOL-GUEST", "signal": -78, "target": False},
    {"ssid": "MIWIFI", "signal": -72, "target": False},
    {"ssid": "LAB-ROUTER-01", "signal": -40, "target": True},
    {"ssid": "ANDROID-HOTSPOT", "signal": -81, "target": False},
]

TARGET_PASSWORD = "ctos_lab_demo_2025"

# Профили «словаря»: только скорость и число попыток в симуляции
DICT_PROFILES: dict[str, dict[str, int | str]] = {
    "fast": {
        "max_attempts": 52,
        "delay_ms": 88,
        "label": "FAST DICT (sim) — fewer attempts",
    },
    "deep": {
        "max_attempts": 96,
        "delay_ms": 52,
        "label": "DEEP SCAN (sim) — more attempts",
    },
}

DEFAULT_PROFILE = "fast"

HANDSHAKE_PHASES: list[str] = [
    "[ASSOC] Joining BSS (simulated)…",
    "[EAPOL] 4-way handshake stub captured (sim)…",
    "[MIC] Message integrity check — pass (sim)…",
    "[PMK] Queuing PSK candidates (sim)…",
]

FAIL_REASONS_NON_TARGET: list[str] = [
    "Reason (sim): No matching PMK in the loaded dictionary.",
    "Reason (sim): AP-side rate limit / lockout — attempt budget exhausted.",
    "Reason (sim): Key derivation mismatch (WPA3 / enterprise stub).",
    "Reason (sim): Dictionary exhausted — try another profile or target (lab only).",
]

EDUCATION_APPEND = (
    "\n\n---\n"
    "SIMULATION ONLY: no real Wi-Fi traffic, captures, or cracking is performed.\n"
    "Use these skills only on networks you own or are authorized to test.\n"
)


def get_profile(profile_key: str) -> dict[str, int | str]:
    return DICT_PROFILES.get(profile_key, DICT_PROFILES[DEFAULT_PROFILE])


# Тур INFO (как в других модулях): ключ → текст; FINAL открывает итоговую панель
INFO_PAGES: list[tuple[str, str]] = [
    (
        "NETWORKS",
        "СПИСОК СЕТЕЙ\n\n"
        "Имитация сканера: появляются вымышленные SSID и уровень сигнала (dBm).\n"
        "Реального доступа к Wi‑Fi адаптеру нет — это только интерфейс симуляции.\n"
        "Выберите сеть, чтобы запустить сценарий (в лаборатории «успех» задан для одной сети).",
    ),
    (
        "PROFILE",
        "FAST / DEEP\n\n"
        "Профиль меняет только число попыток и паузу между строками в логе.\n"
        "DEEP — дольше и больше строк; FAST — короче.\n"
        "Никаких реальных словарей и перебора по эфиру не выполняется.",
    ),
    (
        "LOG",
        "ATTACK LOG\n\n"
        "Здесь выводятся фазы ASSOC / EAPOL / MIC / PMK и строки «перебора».\n"
        "Все строки сгенерированы; на фоне — декоративный значок Wi‑Fi (цвет и «уровень» "
        "зависят от хода симуляции).\n"
        "Текст лога читается поверх фона.",
    ),
    (
        "MAP",
        "NETWORK MAP\n\n"
        "Схема узлов вокруг «YOU»: учебная картинка топологии.\n"
        "Подсветка и подпись ROUTER показывают выбранный SSID (симуляция).",
    ),
    (
        "PROGRESS",
        "PROGRESS\n\n"
        "Общий прогресс сценария: фазы рукопожатия и «словарная» часть.\n"
        "Нижняя полоса не отражает реальный взлом — только ход демонстрации.",
    ),
    (
        "INFO",
        "КНОПКА INFO\n\n"
        "Запускает пошаговый тур по элементам этого экрана (как в других модулях CtOS).\n"
        "Клик по затемнению или по текстовой панели — следующий шаг.\n"
        "В конце откроется итоговая справка о легальности и ограничениях симуляции.",
    ),
    ("FINAL", ""),
]

INFO_FINAL_THEORY = (
    "BRUTEFORCE В CtOS\n\n"
    "В реальности подбор пароля к Wi‑Fi без разрешения владельца сети незаконен.\n"
    "Этот модуль — только визуализация для курса: нет захвата handshakes и нет атаки на эфир.\n\n"
    "Защита: длинный пароль, WPA2/WPA3, отключение WPS, обновление прошивки, гостевая сеть для IoT."
)
