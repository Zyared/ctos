"""Загрузка звуков и фоновой музыки (SRP)."""

from __future__ import annotations

import os

import pygame

from ctos.config import MUSIC_FILE, SOUND_DIR


class SoundService:
    def __init__(self) -> None:
        pygame.mixer.init()
        self.music_file = MUSIC_FILE
        self.sounds: dict[str, pygame.mixer.Sound | list[pygame.mixer.Sound]] = {}
        base = SOUND_DIR
        self.sounds["glitch"] = [
            pygame.mixer.Sound(os.path.join(base, "glitch1.wav")),
            pygame.mixer.Sound(os.path.join(base, "glitch2.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch3.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch4.mp3")),
            pygame.mixer.Sound(os.path.join(base, "glitch5.mp3")),
        ]
        self.sounds["error"] = pygame.mixer.Sound(os.path.join(base, "error.mp3"))
        self.sounds["flicker"] = pygame.mixer.Sound(os.path.join(base, "flicker.mp3"))
        self.sounds["boot"] = pygame.mixer.Sound(os.path.join(base, "boot.wav"))
        self.sounds["exit"] = pygame.mixer.Sound(os.path.join(base, "exit.mp3"))
        self.sounds["digital_error"] = pygame.mixer.Sound(os.path.join(base, "digital_error.mp3"))
        self.sounds["glitchy_exploit"] = pygame.mixer.Sound(os.path.join(base, "glitchy_exploit.mp3"))
        try:
            self.sounds["ui_click"] = pygame.mixer.Sound(os.path.join(base, "click.mp3"))
        except (pygame.error, OSError):
            self.sounds["ui_click"] = pygame.mixer.Sound(os.path.join(base, "flicker.mp3"))

        for s in self.sounds["glitch"]:
            s.set_volume(0.05)
        self.sounds["error"].set_volume(0.05)
        self.sounds["flicker"].set_volume(0.05)
        self.sounds["boot"].set_volume(0.8)
        self.sounds["exit"].set_volume(0.4)
        self.sounds["glitchy_exploit"].set_volume(0.4)
        self.sounds["digital_error"].set_volume(0.4)
        self.sounds["ui_click"].set_volume(0.14)

    def play_ui_hover(self) -> None:
        try:
            self.sounds["ui_click"].set_volume(0.06)
            self.sounds["ui_click"].play()
        except (pygame.error, AttributeError):
            pass

    def play_ui_click(self) -> None:
        try:
            self.sounds["ui_click"].set_volume(0.16)
            self.sounds["ui_click"].play()
        except (pygame.error, AttributeError):
            pass

    def start_background_music(self, enabled: bool = True) -> None:
        if not enabled:
            return
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(self.music_file)
            pygame.mixer.music.set_volume(0.22)
            pygame.mixer.music.play(-1)
        except (pygame.error, OSError):
            pass
