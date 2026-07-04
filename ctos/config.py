"""Пути и константы приложения (единая точка для ресурсов и таймингов)."""

from __future__ import annotations

import os

# Корень проекта (родитель каталога пакета ctos/)
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_PKG_DIR)

SOUND_DIR = os.path.join(PROJECT_ROOT, "sound")
MUSIC_FILE = os.path.join(PROJECT_ROOT, "music.mp3")

# Таймаут бездействия до возврата на заставку (мс)
IDLE_TIMEOUT_MS = 120_000  # 2 минуты
