"""Capture reproducible English screenshots for the repository README."""

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

from kivy.clock import Clock
from kivy.core.window import Window
from PIL import ImageGrab

from main import GameScreen, RPSApp

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = RPSApp()

    def screenshot(name: str):
        if sys.platform != "win32":
            Window.screenshot(name=str(OUTPUT / name))
            return

        user32 = ctypes.windll.user32
        handle = user32.FindWindowW(None, app.title)
        if not handle:
            raise RuntimeError("Neon Hands window was not found.")
        rect = wintypes.RECT()
        origin = wintypes.POINT(0, 0)
        if not user32.GetClientRect(handle, ctypes.byref(rect)):
            raise RuntimeError("Could not read the Neon Hands client bounds.")
        if not user32.ClientToScreen(handle, ctypes.byref(origin)):
            raise RuntimeError("Could not locate the Neon Hands client area.")
        bounds = (
            origin.x,
            origin.y,
            origin.x + rect.right,
            origin.y + rect.bottom,
        )
        ImageGrab.grab(bbox=bounds, all_screens=True).save(OUTPUT / name)

    def open_battle(*_):
        app.start_game(3)

    def choose_rock(*_):
        screen = app.root_layer.children[0]
        if isinstance(screen, GameScreen):
            screen.choose("rock")

    def show_victory(*_):
        screen = app.root_layer.children[0]
        if isinstance(screen, GameScreen):
            screen.player_score = 3
            screen.computer_score = 1
            screen.player_score_label.text = "YOU   3"
            screen.computer_score_label.text = "1   COMPUTER"
            screen._finish_match()

    Clock.schedule_once(lambda *_: screenshot("main-menu.png"), 1.6)
    Clock.schedule_once(open_battle, 1.9)
    Clock.schedule_once(choose_rock, 2.5)
    Clock.schedule_once(lambda *_: screenshot("battle-arena.png"), 4.5)
    Clock.schedule_once(show_victory, 4.8)
    Clock.schedule_once(lambda *_: screenshot("victory-screen.png"), 5.45)
    Clock.schedule_once(lambda *_: app.stop(), 5.7)
    app.run()


if __name__ == "__main__":
    main()
