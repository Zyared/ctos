"""
Цвета и тайминги главного экрана CtOS (Watch Dogs / ctOS).
"""

from __future__ import annotations

# --- Сетка фона ---
GRID_BG = "#000000"
GRID_HV = "#0a0c10"
GRID_DIAG = "#0c1016"
GRID_DOT = "#12161e"

# --- Импульсы по сетке ---
PULSE_COLORS = ("#2d5f6c", "#356a78", "#3a5f6a", "#2a5560", "#3d6e7a")

# --- Меню / граф ---
GRAPH_EDGE = "#1a3d4d"
GRAPH_EDGE_DASH = (3, 5)
MENU_NODE_OUTLINE = "#48bfff"
MENU_NODE_FILL = "#050d14"
MENU_ICON = "#9ee8ff"
MENU_LABEL = "#6a9aad"
MENU_HOVER_OUTLINE = "#00e5ff"
MENU_HOVER_FILL = "#0a1a22"
MENU_HOVER_ICON = "#ffffff"
MENU_HOVER_LABEL = "#b8f0ff"

LOGO_OUTER = "#003344"
LOGO_RING = "#00b8d4"
LOGO_MARK = "#e8fdff"

HUD_TITLE = "#7fd8f0"
HUD_MIVLGU = "#b8e8f5"

EXIT_OUTLINE = "#cc2233"
EXIT_FILL = "#0a0508"
EXIT_FILL_HOVER = "#2a1018"
EXIT_TEXT = "#ff5566"

# --- Тайминги ---
GRAPH_MOTION_MS = 78
WD_GRID_STEP = 56
GRID_PULSE_MS = 48
GRID_PULSE_COUNT = 8

PROFILER_ROTATE_MS = 6500
FEED_ROTATE_MS = 4200
MAP_PULSE_MS = 4800

# --- Profiler (вымышленные данные) ---
# name, role, clearance, uid_stub, status_line
PROFILER_ROWS: list[tuple[str, str, str, str, str]] = [
    ("A. NEMO", "FIELD ANALYST", "CLEARANCE: L3 // SECTOR 7", "UID 0x7a4f…c2", "THREAT: ELEVATED // WATCH"),
    ("B. KOVACS", "CONTRACTOR", "CLEARANCE: L2 // REMOTE", "UID 0x91be…8a", "COMMS: ENCRYPTED"),
    ("C. OKONKWO", "SYSADMIN", "CLEARANCE: L4 // CORE", "UID 0x44d1…f0", "ACCESS: ROOT SHELL IDLE"),
    ("D. VEGA", "PENTEST", "CLEARANCE: L3 // AUDIT", "UID 0x2c8e…11", "SESSION: BENCHMARK MODE"),
    ("E. PARK", "ANALYST", "CLEARANCE: L1 // JUNIOR", "UID 0xb903…7d", "PROFILE: LOW RISK"),
    ("F. ORLOV", "NOC", "CLEARANCE: L3 // NOC-2", "UID 0x6e22…aa", "RELAY: 3x HANDSHAKE OK"),
    ("G. SILVA", "REDACT", "CLEARANCE: L4 // SIGINT", "UID [REDACTED]", "TRACE: MASKED"),
]

# --- Карта: узлы (0..1), код на карте, полное имя района ---
# x, y, code, district_name
MAP_NODES: list[tuple[float, float, str, str]] = [
    (0.14, 0.28, "NL", "NORTH LOOP"),
    (0.78, 0.20, "WD", "THE WARDS"),
    (0.88, 0.62, "IP", "INDUSTRIAL PORT"),
    (0.42, 0.78, "SB", "SOUTH BRIDGE"),
    (0.22, 0.58, "MZ", "MIDTOWN"),
    (0.55, 0.42, "CT", "CENTRAL"),
    (0.68, 0.85, "ER", "EAST RIVER"),
]

# Рёбра графа района (индексы в MAP_NODES)
MAP_EDGES: list[tuple[int, int]] = [
    (0, 4),
    (4, 5),
    (5, 1),
    (1, 2),
    (2, 6),
    (6, 3),
    (3, 4),
    (5, 2),
    (4, 6),
]

# Декор: «магистрали» внутри рамки (нормализованные координаты)
MAP_STREETS: list[tuple[float, float, float, float]] = [
    (0.05, 0.45, 0.95, 0.52),
    (0.48, 0.08, 0.52, 0.92),
    (0.12, 0.70, 0.88, 0.18),
]

MAP_TITLE = "CHICAGO LITE // DISTRICT MESH"
MAP_RISK_PREFIX = "ACTIVE SECTOR"

# --- Лента уведомлений ---
FEED_LINES: list[str] = [
    "[NET] Handshake observed // VLAN 12",
    "[IDS] Anomaly score: LOW",
    "[CTOS] Remote shell session: IDLE",
    "[GEO] District relay: STABLE",
    "[SEC] Token refresh: OK",
    "[NET] ARP table sync complete",
    "[LOG] Policy engine: COMPLIANT",
    "[CTOS] Profiler sync: 0.3s",
]

HUD_MAP_DIM = "#4a6a78"
HUD_MAP_ACCENT = "#6a9aad"
HUD_MAP_STREET = "#152028"

# --- Общая палитра модулей-сценариев (BRUTEFORCE / DATA EXFIL / NETWORK SNIFFER) ---
# Единый источник цвета для всех экранов модулей, чтобы они выглядели как части
# одной ОС, а не как отдельные несвязанные приложения.
ACCENT = "#48bfff"           # тот же акцент, что и MENU_NODE_OUTLINE в главном меню
ACCENT_BRIGHT = "#bfeaff"
HOVER_OUTLINE = "#88d9ff"    # обводка кнопки при наведении
PANEL_BG = "#050b11"
PANEL_OUTLINE = "#2a6a8a"
TEXT = "#d9e7ef"
TEXT_DIM = "#666666"
TEXT_BRIGHT = "#bfeaff"
HEADER = "#6fbad8"
BUTTON_HOVER = "#0b2b3a"
INFO_BG = "#05080c"
INFO_TEXT = "#aee6ff"

# Смысловые акценты: опасность/атакующая сторона и защищённое состояние —
# используются везде одинаково (DATA EXFIL, EXIT-подобные предупреждения и т.п.)
DANGER = "#ff4444"
DANGER_BRIGHT = "#ff8888"
SUCCESS = "#33cc66"
SUCCESS_BRIGHT = "#7dffab"

# --- Модуль BRUTEFORCE (алиасы общей палитры — не трогаем bruteforce.py) ---
BF_PANEL_BG = PANEL_BG
BF_PANEL_OUTLINE = PANEL_OUTLINE
BF_ACCENT = ACCENT
BF_TEXT = TEXT
BF_TEXT_DIM = TEXT_DIM
BF_TEXT_BRIGHT = TEXT_BRIGHT
BF_HEADER = HEADER
BF_BUTTON_HOVER = BUTTON_HOVER
BF_MAP_LINE = "#2a6a8a"
BF_MAP_BG = "#03070c"
BF_EDU_BG = "#020b13"
BF_EDU_PANEL = "#020509"
BF_AMBIENT_BG = "#030508"
BF_AMBIENT_STRIP = "#061018"
BF_AMBIENT_STRIP_OUTLINE = "#0f1a22"
BF_WAVE_BAR_SIG = "#1a3545"
BF_WAVE_BAR_LOAD = "#1a3038"
BF_WAVE_BAR_LOAD_HOT = "#1a4a3a"
BF_AMBIENT_LABEL = "#2a4555"
