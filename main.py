"""Modern, animated mobile Rock Paper Scissors game built with Kivy.

The interface uses transparent 3D-rendered glove sprites while movement stays
lightweight through a spring/damping physics loop and impact particles.
"""

import math
import os
from secrets import SystemRandom
from typing import ClassVar

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    PopMatrix,
    PushMatrix,
    Rectangle,
    Rotate,
    RoundedRectangle,
    Scale,
    Translate,
)
from kivy.metrics import dp
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    StringProperty,
)
from kivy.storage.dictstore import DictStore
from kivy.storage.jsonstore import JsonStore
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.widget import Widget
from kivy.utils import platform

from game_logic import CHOICES, score_round
from integrity import verify_bundled_assets

__version__ = "1.0.0"

if platform not in ("android", "ios"):
    Window.size = (390, 780)
Window.clearcolor = (0.12, 0.14, 0.18, 1)

# Low-contrast, soft mobile palette.  The names are kept stable so the rest of
# the game code remains readable.
NAVY = (0.12, 0.14, 0.18, 1)
WHITE = (0.96, 0.95, 0.93, 1)
MUTED = (0.69, 0.70, 0.73, 1)
CYAN = (0.44, 0.70, 0.67, 1)
VIOLET = (0.57, 0.53, 0.72, 1)
CORAL = (0.82, 0.55, 0.53, 1)
GOLD = (0.82, 0.70, 0.49, 1)

APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ASSET_DIRECTORY = os.path.join(APP_DIRECTORY, "assets")
PLAYER_SHEET_PATH = os.path.join(ASSET_DIRECTORY, "player-glove-3d-sheet-v2.png")
COMPUTER_SHEET_PATH = os.path.join(ASSET_DIRECTORY, "computer-glove-3d-sheet-v2.png")
RNG = SystemRandom()


def bounded_volume(value, default):
    """Convert persisted volume values without accepting NaN or infinity."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number):
        return default
    return max(0.0, min(1.0, number))


def make_label(text, size=16, color=WHITE, bold=False, **kwargs):
    return Label(
        text=text,
        font_size=f"{size}sp",
        color=color,
        bold=bold,
        halign="center",
        valign="middle",
        **kwargs,
    )


def active_audio():
    app = App.get_running_app()
    return getattr(app, "audio", None) if app else None


class AudioManager:
    """Loads original WAV assets and persists separate music/SFX volumes."""

    def __init__(self, asset_directory, settings_store):
        self.store = settings_store
        defaults = {"music": 0.34, "sfx": 0.72}
        try:
            saved = self.store.get("audio") if self.store.exists("audio") else defaults
        except (KeyError, OSError, TypeError, ValueError):
            saved = defaults
        if not isinstance(saved, dict):
            saved = defaults
        self.music_volume = bounded_volume(saved.get("music"), 0.34)
        self.sfx_volume = bounded_volume(saved.get("sfx"), 0.72)
        audio_directory = os.path.join(asset_directory, "audio")
        self.music_tracks = {
            "menu": SoundLoader.load(os.path.join(audio_directory, "soft_loop.wav")),
            "battle": SoundLoader.load(
                os.path.join(audio_directory, "battle_loop.wav")
            ),
        }
        self.current_track = None
        self._pending_track = None
        self._fade_phase = None
        self._fade_event = None
        self._fade_duration = 0.34
        self._restore_music_event = None
        self.effects = {
            "click": SoundLoader.load(os.path.join(audio_directory, "soft_click.wav")),
            "whoosh": SoundLoader.load(
                os.path.join(audio_directory, "hand_whoosh.wav")
            ),
            "reveal": SoundLoader.load(
                os.path.join(audio_directory, "reveal_swish.wav")
            ),
            "victory": SoundLoader.load(
                os.path.join(audio_directory, "victory_fanfare.wav")
            ),
            "defeat": SoundLoader.load(
                os.path.join(audio_directory, "defeat_sting.wav")
            ),
        }
        for music in self.music_tracks.values():
            if music:
                music.loop = True
                music.volume = self.music_volume
        self.set_sfx_volume(self.sfx_volume, save=False)

    def start_music(self, *_):
        track_name = self.current_track or "menu"
        music = self.music_tracks.get(track_name)
        if music and music.state != "play":
            music.volume = self.music_volume
            music.play()

    def switch_music(self, track_name, fade_duration=0.34):
        """Cross-screen music change with a short dip instead of a hard cut."""
        if track_name not in self.music_tracks:
            return
        current = self.music_tracks.get(self.current_track)
        target = self.music_tracks.get(track_name)
        if self.current_track == track_name and target and target.state == "play":
            return
        if self._fade_event is not None:
            self._fade_event.cancel()
            self._fade_event = None
        self._pending_track = track_name
        self._fade_duration = max(0.08, float(fade_duration))
        if current and current.state == "play" and self.music_volume > 0.001:
            self._fade_phase = "out"
        else:
            self._begin_pending_track()
        self._fade_event = Clock.schedule_interval(self._step_music_fade, 1 / 30)

    def _begin_pending_track(self):
        old_music = self.music_tracks.get(self.current_track)
        if old_music:
            old_music.stop()
        self.current_track = self._pending_track
        new_music = self.music_tracks.get(self.current_track)
        if new_music:
            new_music.stop()
            new_music.volume = 0
            new_music.play()
        self._fade_phase = "in"

    def _step_music_fade(self, dt):
        music = self.music_tracks.get(self.current_track)
        step = max(self.music_volume, 0.01) * dt / self._fade_duration
        if self._fade_phase == "out":
            if not music:
                self._begin_pending_track()
            else:
                music.volume = max(0, music.volume - step)
                if music.volume <= 0.002:
                    self._begin_pending_track()
        elif self._fade_phase == "in":
            if not music:
                self._finish_music_fade()
                return False
            music.volume = min(self.music_volume, music.volume + step)
            if music.volume >= self.music_volume - 0.002:
                music.volume = self.music_volume
                self._finish_music_fade()
                return False
        return True

    def _finish_music_fade(self):
        self._pending_track = None
        self._fade_phase = None
        if self._fade_event is not None:
            self._fade_event.cancel()
            self._fade_event = None

    def stop_music(self):
        if self._restore_music_event is not None:
            self._restore_music_event.cancel()
            self._restore_music_event = None
        if self._fade_event is not None:
            self._fade_event.cancel()
            self._fade_event = None
        self._fade_phase = None
        self._pending_track = None
        for music in self.music_tracks.values():
            if music:
                music.stop()

    def play(self, name):
        sound = self.effects.get(name)
        if sound and self.sfx_volume > 0.001:
            sound.stop()
            sound.volume = self.sfx_volume
            sound.play()

    def play_match_result(self, won):
        """Make the result sting clear by briefly ducking the music."""
        effect_name = "victory" if won else "defeat"
        sound = self.effects.get(effect_name)
        if not sound or self.sfx_volume <= 0.001:
            return
        music = self.music_tracks.get(self.current_track)
        if music and music.state == "play":
            music.volume = self.music_volume * 0.24
        self.play(effect_name)
        if self._restore_music_event is not None:
            self._restore_music_event.cancel()
        delay = 3.05 if won else 2.35
        self._restore_music_event = Clock.schedule_once(
            self._restore_music_volume, delay
        )

    def _restore_music_volume(self, *_):
        self._restore_music_event = None
        music = self.music_tracks.get(self.current_track)
        if music and self._fade_event is None:
            music.volume = self.music_volume

    def set_music_volume(self, value, save=True):
        self.music_volume = bounded_volume(value, self.music_volume)
        current = self.music_tracks.get(self.current_track)
        if current and self._fade_event is None:
            current.volume = self.music_volume
        if save:
            self._save()

    def set_sfx_volume(self, value, save=True):
        self.sfx_volume = bounded_volume(value, self.sfx_volume)
        for sound in self.effects.values():
            if sound:
                sound.volume = self.sfx_volume
        if save:
            self._save()

    def _save(self):
        try:
            self.store.put("audio", music=self.music_volume, sfx=self.sfx_volume)
        except (OSError, TypeError, ValueError):
            # Storage failure must not break gameplay or the live volume controls.
            return


class CardButton(Button):
    accent = ListProperty(CYAN)
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", WHITE)
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)
        self.bind(
            pos=self.redraw,
            size=self.redraw,
            state=self.redraw,
            accent=self.redraw,
            selected=self.redraw,
        )
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        pressed = self.state == "down"
        with self.canvas.before:
            Color(0.02, 0.025, 0.035, 0.18)
            RoundedRectangle(
                pos=(self.x, self.y - dp(3)),
                size=self.size,
                radius=[dp(18)],
            )
            Color(1, 1, 1, 0.15 if pressed or self.selected else 0.095)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
            Color(
                self.accent[0],
                self.accent[1],
                self.accent[2],
                0.55 if pressed else 0.22,
            )
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(20)),
                width=1.15,
            )

    def on_release(self):
        audio = active_audio()
        if audio:
            audio.play("click")


class PillButton(Button):
    accent = ListProperty(VIOLET)

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", WHITE)
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)
        self.bind(
            pos=self.redraw, size=self.redraw, state=self.redraw, accent=self.redraw
        )
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        factor = 0.82 if self.state == "down" else 1.0
        with self.canvas.before:
            Color(
                self.accent[0] * factor,
                self.accent[1] * factor,
                self.accent[2] * factor,
                1,
            )
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.height / 2])

    def on_release(self):
        audio = active_audio()
        if audio:
            audio.play("click")


class SpringBody:
    """Small deterministic spring body: force = -kx - cv."""

    def __init__(self, widget, stiffness=190.0, damping=18.0):
        self.widget = widget
        self.stiffness = stiffness
        self.damping = damping
        self.target_y = 0.0
        self.velocity_y = 0.0
        self.target_angle = 0.0
        self.velocity_angle = 0.0

    def kick(self, velocity_y=0, angular_velocity=0, target_y=0):
        self.velocity_y += velocity_y
        self.velocity_angle += angular_velocity
        self.target_y = target_y

    def update(self, dt):
        dt = min(dt, 1 / 30)
        ay = (
            self.stiffness * (self.target_y - self.widget.motion_y)
            - self.damping * self.velocity_y
        )
        aa = (
            130.0 * (self.target_angle - self.widget.hand_angle)
            - 15.0 * self.velocity_angle
        )
        self.velocity_y += ay * dt
        self.velocity_angle += aa * dt
        self.widget.motion_y += self.velocity_y * dt
        self.widget.hand_angle += self.velocity_angle * dt


class SpriteGloveHand(Widget):
    """A single 3D-rendered hand selected from a three-cell texture sheet."""

    gesture = StringProperty("rock")
    sprite_sheet = StringProperty("")
    upside_down = BooleanProperty(False)
    motion_y = NumericProperty(0)
    hand_angle = NumericProperty(0)
    hand_scale = NumericProperty(1)

    gesture_index: ClassVar[dict[str, int]] = {"rock": 0, "paper": 1, "scissors": 2}
    _sheet_cache: ClassVar[dict[str, object]] = {}
    _region_cache: ClassVar[dict[tuple[str, str], object]] = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._gesture_textures = {}
        self._load_sheet()
        self.bind(
            pos=self.redraw,
            size=self.redraw,
            gesture=self.redraw,
            upside_down=self.redraw,
            motion_y=self.redraw,
            hand_angle=self.redraw,
            hand_scale=self.redraw,
            opacity=self.redraw,
        )
        self.redraw()

    def _load_sheet(self):
        if not self.sprite_sheet:
            return
        self._gesture_textures = {
            gesture: self.gesture_texture(self.sprite_sheet, gesture)
            for gesture in self.gesture_index
        }

    @classmethod
    def gesture_texture(cls, sheet_path, gesture):
        """Reuse decoded sheets and regions across every visible hand."""
        if gesture not in cls.gesture_index:
            raise ValueError(f"Unknown hand gesture: {gesture}")
        cache_key = (sheet_path, gesture)
        if cache_key not in cls._region_cache:
            if sheet_path not in cls._sheet_cache:
                cls._sheet_cache[sheet_path] = CoreImage(sheet_path).texture
            texture = cls._sheet_cache[sheet_path]
            cell_width = texture.width // 3
            index = cls.gesture_index[gesture]
            cls._region_cache[cache_key] = texture.get_region(
                index * cell_width, 0, cell_width, texture.height
            )
        return cls._region_cache[cache_key]

    def show(self, gesture):
        self.gesture = gesture

    def redraw(self, *_):
        self.canvas.clear()
        texture = self._gesture_textures.get(self.gesture)
        if texture is None:
            return
        side = min(self.width * 0.92, self.height * 0.99)
        rotation = self.hand_angle + (180 if self.upside_down else 0)
        center_x = self.center_x
        center_y = self.center_y + self.motion_y
        with self.canvas:
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=rotation, origin=(0, 0))
            Scale(self.hand_scale, self.hand_scale, 1)

            # Alpha-masked sprite shadow gives depth without a circular glow.
            Color(0.025, 0.03, 0.04, 0.26 * self.opacity)
            Rectangle(
                pos=(-side / 2 + dp(4), -side / 2 - dp(7)),
                size=(side, side),
                texture=texture,
            )
            Color(1, 1, 1, self.opacity)
            Rectangle(
                pos=(-side / 2, -side / 2),
                size=(side, side),
                texture=texture,
            )
            PopMatrix()


class GestureChoice(ButtonBehavior, FloatLayout):
    """Large vertical choice tile: 3D hand above, simple label below."""

    gesture = StringProperty("rock")
    title = StringProperty("ROCK")
    sprite_sheet = StringProperty("")
    accent = ListProperty(CYAN)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        gesture_scales = {"rock": 0.90, "paper": 0.68, "scissors": 0.68}
        self.hand = SpriteGloveHand(
            gesture=self.gesture,
            sprite_sheet=self.sprite_sheet,
            hand_scale=gesture_scales[self.gesture],
            size_hint=(None, None),
            width=self.width,
            height=dp(108),
        )
        self.add_widget(self.hand)
        self.caption = make_label(
            self.title,
            15,
            WHITE,
            True,
            size_hint=(None, None),
            width=self.width,
            height=dp(30),
        )
        self.caption.bind(
            size=lambda widget, value: setattr(widget, "text_size", value)
        )
        self.add_widget(self.caption)
        self.bind(
            pos=self.redraw,
            size=self.redraw,
            state=self.redraw,
            accent=self.redraw,
        )
        self.bind(pos=self._layout_content, size=self._layout_content)
        self._layout_content()
        self.redraw()

    def _layout_content(self, *_):
        """Use absolute card coordinates so relayout animations cannot drift."""
        self.hand.size = (self.width, dp(108))
        self.hand.pos = (self.x, self.top - dp(114))
        self.caption.size = (self.width, dp(30))
        self.caption.pos = (self.x, self.y + dp(3))

    def on_release(self):
        audio = active_audio()
        if audio:
            audio.play("click")

    def redraw(self, *_):
        self.canvas.before.clear()
        pressed = self.state == "down"
        with self.canvas.before:
            Color(0.02, 0.025, 0.035, 0.13)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=[dp(18)],
            )
            Color(
                self.accent[0],
                self.accent[1],
                self.accent[2],
                0.13 if pressed else 0.055,
            )
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
            Color(1, 1, 1, 0.08 if pressed else 0.045)
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(18)),
                width=0.8,
            )


class ParticleBurst(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.particles = []

    def burst(self, color, count=22):
        self.particles = []
        for _ in range(count):
            angle = RNG.uniform(0, math.tau)
            speed = RNG.uniform(dp(55), dp(180))
            self.particles.append(
                [
                    self.center_x,
                    self.center_y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    RNG.uniform(dp(3), dp(7)),
                    1.0,
                    color,
                ]
            )
        Clock.unschedule(self._step)
        Clock.schedule_interval(self._step, 1 / 60)

    def _step(self, dt):
        alive = False
        for particle in self.particles:
            particle[2] *= 0.985
            particle[3] = particle[3] * 0.985 - dp(120) * dt
            particle[0] += particle[2] * dt
            particle[1] += particle[3] * dt
            particle[5] -= dt * 1.45
            alive |= particle[5] > 0
        self.canvas.clear()
        with self.canvas:
            for x, y, _, _, radius, life, color in self.particles:
                if life > 0:
                    Color(color[0], color[1], color[2], life)
                    Ellipse(
                        pos=(x - radius, y - radius),
                        size=(radius * 2, radius * 2),
                    )
        return alive


class ConfettiCelebration(Widget):
    """Rectangular confetti fired from both sides after a match victory."""

    palette = (CYAN, VIOLET, CORAL, GOLD, WHITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pieces = []

    def celebrate(self, count=86):
        self.pieces = []
        for index in range(count):
            from_left = index % 2 == 0
            origin_x = self.x + self.width * (0.16 if from_left else 0.84)
            origin_y = self.y + self.height * RNG.uniform(0.28, 0.39)
            horizontal = RNG.uniform(dp(45), dp(205))
            velocity_x = horizontal if from_left else -horizontal
            self.pieces.append(
                [
                    origin_x + RNG.uniform(-dp(18), dp(18)),
                    origin_y,
                    velocity_x,
                    RNG.uniform(dp(280), dp(520)),
                    RNG.uniform(dp(4), dp(8)),
                    RNG.uniform(dp(9), dp(17)),
                    RNG.uniform(2.4, 3.6),
                    RNG.choice(self.palette),
                    RNG.uniform(0, 180),
                    RNG.uniform(-420, 420),
                ]
            )
        Clock.unschedule(self._step)
        Clock.schedule_interval(self._step, 1 / 60)

    def _step(self, dt):
        alive = False
        for piece in self.pieces:
            piece[2] *= 0.992
            piece[3] -= dp(335) * dt
            piece[0] += piece[2] * dt
            piece[1] += piece[3] * dt
            piece[6] -= dt
            piece[8] += piece[9] * dt
            alive |= piece[6] > 0 and piece[1] > self.y - dp(30)
        self.canvas.clear()
        with self.canvas:
            for x, y, _, _, width, height, life, color, angle, _ in self.pieces:
                if life <= 0 or y <= self.y - dp(30):
                    continue
                alpha = min(1, life * 1.8)
                PushMatrix()
                Translate(x, y)
                Rotate(angle=angle, origin=(0, 0))
                Color(color[0], color[1], color[2], alpha)
                RoundedRectangle(
                    pos=(-width / 2, -height / 2),
                    size=(width, height),
                    radius=[dp(1.5)],
                )
                PopMatrix()
        return alive


class TintedLabel(Label):
    """A compact glass label for scores, rounds and arena status."""

    accent = ListProperty(CYAN)
    fill_alpha = NumericProperty(0.10)

    def __init__(self, **kwargs):
        kwargs.setdefault("color", WHITE)
        kwargs.setdefault("bold", True)
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(
            pos=self.redraw,
            size=self.redraw,
            accent=self.redraw,
            fill_alpha=self.redraw,
        )
        self.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.02, 0.025, 0.05, 0.22)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=[dp(15)],
            )
            Color(
                self.accent[0],
                self.accent[1],
                self.accent[2],
                self.fill_alpha,
            )
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(15)])
            Color(self.accent[0], self.accent[1], self.accent[2], 0.30)
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(15)),
                width=0.9,
            )


class Arena(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.computer_label = make_label(
            "COMPUTER",
            10,
            CORAL,
            True,
            size_hint=(None, None),
        )
        self.add_widget(self.computer_label)
        self.computer_hand = SpriteGloveHand(
            upside_down=True,
            sprite_sheet=COMPUTER_SHEET_PATH,
            size_hint=(None, None),
        )
        self.add_widget(self.computer_hand)
        self.versus = TintedLabel(
            text="VS",
            font_size="13sp",
            color=GOLD,
            accent=GOLD,
            fill_alpha=0.16,
            size_hint=(None, None),
        )
        self.add_widget(self.versus)
        self.player_hand = SpriteGloveHand(
            sprite_sheet=PLAYER_SHEET_PATH,
            size_hint=(None, None),
        )
        self.add_widget(self.player_hand)
        self.player_label = make_label(
            "YOU",
            10,
            CYAN,
            True,
            size_hint=(None, None),
        )
        self.add_widget(self.player_label)
        self.bind(pos=self._layout_arena, size=self._layout_arena)
        self.bind(pos=self.redraw, size=self.redraw)
        self._layout_arena()
        self.redraw()

    def _layout_arena(self, *_):
        gap = dp(24)
        panel_height = max(0, (self.height - gap) / 2)
        bottom_y = self.y
        top_y = self.y + panel_height + gap
        hand_width = max(0, self.width - dp(32))

        self.computer_label.pos = (self.x + dp(16), self.top - dp(31))
        self.computer_label.size = (hand_width, dp(24))
        self.computer_hand.pos = (self.x + dp(16), top_y + dp(5))
        self.computer_hand.size = (hand_width, max(0, panel_height - dp(24)))

        self.player_label.pos = (self.x + dp(16), bottom_y + dp(7))
        self.player_label.size = (hand_width, dp(24))
        self.player_hand.pos = (self.x + dp(16), bottom_y + dp(23))
        self.player_hand.size = (hand_width, max(0, panel_height - dp(24)))

        self.versus.size = (dp(68), dp(42))
        self.versus.pos = (self.center_x - dp(34), self.center_y - dp(21))

    def redraw(self, *_):
        self.canvas.before.clear()
        gap = dp(24)
        panel_height = max(0, (self.height - gap) / 2)
        panel_x = self.x + dp(2)
        panel_width = max(0, self.width - dp(4))
        top_y = self.y + panel_height + gap
        with self.canvas.before:
            Color(0.02, 0.025, 0.05, 0.20)
            RoundedRectangle(
                pos=(panel_x, self.y - dp(3)),
                size=(panel_width, panel_height),
                radius=[dp(24)],
            )
            RoundedRectangle(
                pos=(panel_x, top_y - dp(3)),
                size=(panel_width, panel_height),
                radius=[dp(24)],
            )

            Color(CYAN[0], CYAN[1], CYAN[2], 0.095)
            RoundedRectangle(
                pos=(panel_x, self.y),
                size=(panel_width, panel_height),
                radius=[dp(24)],
            )
            Color(CYAN[0], CYAN[1], CYAN[2], 0.28)
            Line(
                rounded_rectangle=(panel_x, self.y, panel_width, panel_height, dp(24)),
                width=0.9,
            )

            Color(CORAL[0], CORAL[1], CORAL[2], 0.095)
            RoundedRectangle(
                pos=(panel_x, top_y),
                size=(panel_width, panel_height),
                radius=[dp(24)],
            )
            Color(CORAL[0], CORAL[1], CORAL[2], 0.28)
            Line(
                rounded_rectangle=(panel_x, top_y, panel_width, panel_height, dp(24)),
                width=0.9,
            )

            Color(GOLD[0], GOLD[1], GOLD[2], 0.24)
            Line(
                points=(
                    self.center_x - dp(58),
                    self.center_y,
                    self.center_x - dp(42),
                    self.center_y,
                ),
                width=1.1,
            )
            Line(
                points=(
                    self.center_x + dp(42),
                    self.center_y,
                    self.center_x + dp(58),
                    self.center_y,
                ),
                width=1.1,
            )


class GameScreen(FloatLayout):
    choices = CHOICES

    def __init__(self, target_score=3, on_menu=None, **kwargs):
        super().__init__(**kwargs)
        self.target_score = target_score
        self.on_menu = on_menu
        self.player_score = 0
        self.computer_score = 0
        self.round_number = 1
        self.locked = False
        self._backdrop_elapsed = 0.0
        self.backdrop = AnimatedMenuBackdrop()
        self.backdrop.opacity = 0.76
        self.add_widget(self.backdrop)

        self.content = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16), dp(18), dp(14)],
            spacing=dp(7),
        )
        self.add_widget(self.content)
        self._build_header()
        self.arena = Arena()
        self.arena.opacity = 0
        self.arena.size_hint_y = None
        self.arena.height = 0
        self.arena.player_hand.hand_scale = 0.84
        self.arena.computer_hand.hand_scale = 0.84
        self.arena_revealed = False
        self.content.add_widget(self.arena)
        self.status = TintedLabel(
            text="Choose your move",
            font_size="18sp",
            color=WHITE,
            accent=VIOLET,
            fill_alpha=0.08,
            size_hint_y=None,
            height=dp(44),
        )
        self.content.add_widget(self.status)
        self._build_choices()

        self.particles = ParticleBurst()
        self.add_widget(self.particles)
        self.confetti = ConfettiCelebration()
        self.add_widget(self.confetti)
        self.player_physics = SpringBody(self.arena.player_hand)
        self.computer_physics = SpringBody(self.arena.computer_hand)
        self._physics_event = Clock.schedule_interval(self._physics_step, 1 / 60)

    def _build_header(self):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        back = CardButton(
            text="‹",
            font_size="28sp",
            size_hint_x=None,
            width=dp(48),
            accent=VIOLET,
        )
        back.bind(on_release=lambda *_: self.on_menu() if self.on_menu else None)
        row.add_widget(back)
        title_box = BoxLayout(orientation="vertical")
        title_box.add_widget(
            make_label(
                "[color=9BE7DD]NEON[/color] [color=FFF8EC]ARENA[/color]",
                19,
                WHITE,
                True,
                markup=True,
            )
        )
        mode = (
            "SINGLE ROUND"
            if self.target_score == 1
            else f"FIRST TO {self.target_score}"
        )
        title_box.add_widget(make_label(mode, 10, MUTED, True))
        row.add_widget(title_box)
        self.round_label = TintedLabel(
            text="ROUND 1",
            font_size="9sp",
            color=CYAN,
            accent=CYAN,
            fill_alpha=0.09,
            size_hint=(None, None),
            size=(dp(70), dp(34)),
            pos_hint={"center_y": 0.5},
        )
        row.add_widget(self.round_label)
        self.content.add_widget(row)

        score = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        self.player_score_label = TintedLabel(
            text="YOU   0",
            font_size="15sp",
            color=CYAN,
            accent=CYAN,
            fill_alpha=0.105,
        )
        score.add_widget(self.player_score_label)
        score.add_widget(
            make_label(
                "VS",
                11,
                GOLD,
                True,
                size_hint_x=None,
                width=dp(32),
            )
        )
        self.computer_score_label = TintedLabel(
            text="0   COMPUTER",
            font_size="15sp",
            color=CORAL,
            accent=CORAL,
            fill_alpha=0.105,
        )
        score.add_widget(self.computer_score_label)
        self.content.add_widget(score)

    def _build_choices(self):
        self.choice_panel = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(580),
            spacing=dp(12),
            padding=[0, dp(3), 0, dp(3)],
        )
        self.choice_buttons = []
        data = (
            ("ROCK", CYAN),
            ("PAPER", VIOLET),
            ("SCISSORS", CORAL),
        )
        for gesture, (text, accent) in zip(self.choices, data):
            button = GestureChoice(
                gesture=gesture,
                title=text,
                accent=accent,
                sprite_sheet=PLAYER_SHEET_PATH,
            )
            button.bind(on_release=lambda _, move=gesture: self.choose(move))
            self.choice_panel.add_widget(button)
            self.choice_buttons.append(button)
        self.content.add_widget(self.choice_panel)

    def _physics_step(self, dt):
        self._backdrop_elapsed += dt
        self.backdrop.step(self._backdrop_elapsed)
        self.player_physics.update(dt)
        self.computer_physics.update(dt)

    def choose(self, player_move):
        if self.locked:
            return
        self.locked = True
        for button in self.choice_buttons:
            button.disabled = True
        self.status.text = "Get ready..."
        self.status.color = WHITE
        self.status.accent = VIOLET
        self.arena.player_hand.show("rock")
        self.arena.computer_hand.show("rock")
        Animation(opacity=0, height=0, duration=0.26, t="out_quad").start(
            self.choice_panel
        )
        if not self.arena_revealed:
            self.arena_revealed = True
            self.arena.size_hint_y = 1
            Animation(opacity=1, duration=0.38, t="out_quad").start(self.arena)
            Animation(hand_scale=1, duration=0.42, t="out_back").start(
                self.arena.player_hand
            )
            Animation(hand_scale=1, duration=0.42, t="out_back").start(
                self.arena.computer_hand
            )
        Clock.schedule_once(lambda *_: self._countdown(player_move, 0), 0.24)

    def _countdown(self, player_move, step):
        words = ("ROCK!", "PAPER!", "SCISSORS!")
        self.status.text = words[step]
        audio = active_audio()
        if audio:
            audio.play("whoosh")
        direction = 1 if step % 2 == 0 else -1
        self.player_physics.kick(velocity_y=dp(520), angular_velocity=75 * direction)
        self.computer_physics.kick(
            velocity_y=-dp(520), angular_velocity=-75 * direction
        )
        self.arena.versus.font_size = "18sp"
        Animation(font_size=dp(13), duration=0.22, t="out_back").start(
            self.arena.versus
        )
        if step < 2:
            Clock.schedule_once(lambda *_: self._countdown(player_move, step + 1), 0.48)
        else:
            Clock.schedule_once(lambda *_: self._reveal(player_move), 0.48)

    def _reveal(self, player_move):
        computer_move = RNG.choice(self.choices)
        audio = active_audio()
        if audio:
            audio.play("reveal")
        self.arena.player_hand.show(player_move)
        self.arena.computer_hand.show(computer_move)
        self.player_physics.kick(velocity_y=dp(330), angular_velocity=-90)
        self.computer_physics.kick(velocity_y=-dp(330), angular_velocity=90)
        outcome = self._score(player_move, computer_move)
        color = GOLD if outcome == "draw" else CYAN if outcome == "win" else CORAL
        self.particles.burst(color)
        self._update_score(outcome)

    @staticmethod
    def _score(player, computer):
        return score_round(player, computer)

    def _update_score(self, outcome):
        if outcome == "win":
            self.player_score += 1
            self.status.text = "ROUND WON!"
            self.status.color = CYAN
            self.status.accent = CYAN
        elif outcome == "lose":
            self.computer_score += 1
            self.status.text = "COMPUTER WINS THE ROUND"
            self.status.color = CORAL
            self.status.accent = CORAL
        else:
            self.status.text = "DRAW • GO AGAIN!"
            self.status.color = GOLD
            self.status.accent = GOLD
        self.player_score_label.text = f"YOU   {self.player_score}"
        self.computer_score_label.text = f"{self.computer_score}   COMPUTER"

        if (
            self.player_score >= self.target_score
            or self.computer_score >= self.target_score
        ):
            Clock.schedule_once(self._finish_match, 1.15)
        else:
            self.round_number += 1
            self.round_label.text = f"ROUND {self.round_number}"
            Clock.schedule_once(self._next_round, 1.2)

    def _next_round(self, *_):
        self.locked = False
        self.status.text = "Choose your next move"
        self.status.color = WHITE
        self.status.accent = VIOLET
        self.arena_revealed = False
        self.arena.opacity = 0
        self.arena.size_hint_y = None
        self.arena.height = 0
        self.arena.player_hand.hand_scale = 0.84
        self.arena.computer_hand.hand_scale = 0.84
        for button in self.choice_buttons:
            button.disabled = False
        Animation(opacity=1, height=dp(580), duration=0.32, t="out_back").start(
            self.choice_panel
        )

    def _finish_match(self, *_):
        won = self.player_score > self.computer_score
        audio = active_audio()
        if audio:
            audio.play_match_result(won)
        if won:
            self.confetti.celebrate()
        self.status.text = "YOU WIN!" if won else "GAME OVER • COMPUTER WINS"
        self.status.color = CYAN if won else CORAL
        self.status.accent = CYAN if won else CORAL
        self.choice_panel.clear_widgets()
        self.choice_panel.orientation = "horizontal"
        self.choice_panel.padding = [0, 0, 0, 0]
        self.choice_panel.height = dp(66)
        self.choice_panel.opacity = 1
        again = PillButton(text="PLAY AGAIN", font_size="14sp", accent=VIOLET)
        again.bind(on_release=lambda *_: self._restart())
        menu = CardButton(
            text="MODES",
            font_size="14sp",
            accent=CYAN,
            size_hint_x=0.42,
        )
        menu.bind(on_release=lambda *_: self.on_menu() if self.on_menu else None)
        self.choice_panel.add_widget(again)
        self.choice_panel.add_widget(menu)

    def _restart(self):
        replacement = GameScreen(target_score=self.target_score, on_menu=self.on_menu)
        parent = self.parent
        parent.remove_widget(self)
        parent.add_widget(replacement)

    def on_parent(self, _, parent):
        if parent is None and hasattr(self, "_physics_event"):
            self._physics_event.cancel()


class SettingsCard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.03, 0.04, 0.055, 0.28)
            RoundedRectangle(
                pos=(self.x, self.y - dp(7)),
                size=self.size,
                radius=[dp(26)],
            )
            Color(0.16, 0.18, 0.23, 0.98)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(26)])
            Color(1, 1, 1, 0.09)
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(26)),
                width=1,
            )


class SettingsOverlay(FloatLayout):
    def __init__(self, audio, on_close, **kwargs):
        super().__init__(**kwargs)
        self.audio = audio
        self.on_close_callback = on_close
        with self.canvas.before:
            Color(0.025, 0.03, 0.045, 0.76)
            self.dimmer = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._resize_dimmer, size=self._resize_dimmer)

        card = SettingsCard(
            orientation="vertical",
            size_hint=(0.86, None),
            height=dp(350),
            pos_hint={"center_x": 0.5, "center_y": 0.52},
            padding=[dp(24), dp(20), dp(24), dp(18)],
            spacing=dp(10),
        )
        self.add_widget(card)
        card.add_widget(
            make_label(
                "SOUND SETTINGS",
                21,
                WHITE,
                True,
                size_hint_y=None,
                height=dp(38),
            )
        )
        card.add_widget(
            make_label(
                "Adjust music and sound effects separately",
                12,
                MUTED,
                size_hint_y=None,
                height=dp(28),
            )
        )

        self.music_label = make_label(
            "", 14, CYAN, True, size_hint_y=None, height=dp(28)
        )
        card.add_widget(self.music_label)
        music_slider = self._slider(audio.music_volume)
        music_slider.bind(value=self._music_changed)
        card.add_widget(music_slider)

        self.sfx_label = make_label(
            "", 14, CORAL, True, size_hint_y=None, height=dp(28)
        )
        card.add_widget(self.sfx_label)
        sfx_slider = self._slider(audio.sfx_volume)
        sfx_slider.bind(value=self._sfx_changed)
        card.add_widget(sfx_slider)

        close = PillButton(
            text="DONE",
            font_size="14sp",
            accent=VIOLET,
            size_hint_y=None,
            height=dp(52),
        )
        close.bind(on_release=lambda *_: self.on_close_callback(self))
        card.add_widget(close)
        self._refresh_labels()

    @staticmethod
    def _slider(value):
        return Slider(
            min=0,
            max=1,
            value=value,
            step=0.01,
            size_hint_y=None,
            height=dp(34),
            cursor_size=(dp(24), dp(24)),
            background_width=dp(4),
            value_track=True,
            value_track_color=CYAN,
            value_track_width=dp(4),
        )

    def _music_changed(self, _, value):
        self.audio.set_music_volume(value)
        self._refresh_labels()

    def _sfx_changed(self, _, value):
        self.audio.set_sfx_volume(value)
        self._refresh_labels()

    def _refresh_labels(self):
        self.music_label.text = f"MUSIC   {round(self.audio.music_volume * 100)}%"
        self.sfx_label.text = (
            f"HAND + BUTTON SFX   {round(self.audio.sfx_volume * 100)}%"
        )

    def _resize_dimmer(self, *_):
        self.dimmer.pos = self.pos
        self.dimmer.size = self.size

    def on_touch_down(self, touch):
        handled = super().on_touch_down(touch)
        return handled or self.collide_point(*touch.pos)


class MenuGradientBackground(Widget):
    """A richer menu-only gradient; the arena keeps its calmer backdrop."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.graphics.texture import Texture

        bottom = (21, 26, 48, 255)
        middle = (48, 39, 79, 255)
        top = (29, 75, 80, 255)
        pixels = bytearray()
        for row in range(128):
            position = row / 127
            if position < 0.53:
                local = position / 0.53
                start, end = bottom, middle
            else:
                local = (position - 0.53) / 0.47
                start, end = middle, top
            pixels.extend(
                int(start[channel] + (end[channel] - start[channel]) * local)
                for channel in range(4)
            )
        self.gradient_texture = Texture.create(size=(1, 128), colorfmt="rgba")
        self.gradient_texture.blit_buffer(
            bytes(pixels), colorfmt="rgba", bufferfmt="ubyte"
        )
        self.gradient_texture.wrap = "clamp_to_edge"
        self.gradient_texture.mag_filter = "linear"
        self.bind(pos=self.redraw, size=self.redraw)
        self.redraw()

    def redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, texture=self.gradient_texture)


class AmbientTile(Widget):
    """A low-cost floating glass tile used by the animated menu backdrop."""

    angle = NumericProperty(0)
    tone = ListProperty(CYAN)

    def __init__(
        self,
        base_x,
        base_y,
        drift_x,
        drift_y,
        phase,
        base_angle,
        tone,
        gestures,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_x = base_x
        self.base_y = base_y
        self.drift_x = drift_x
        self.drift_y = drift_y
        self.phase = phase
        self.base_angle = base_angle
        self.tone = tone
        self._icon_textures = [
            SpriteGloveHand.gesture_texture(
                PLAYER_SHEET_PATH if index == 0 else COMPUTER_SHEET_PATH,
                gesture,
            )
            for index, gesture in enumerate(gestures)
        ]
        with self.canvas:
            PushMatrix()
            self._translation = Translate(self.center_x, self.center_y)
            self._rotation = Rotate(angle=self.angle, origin=(0, 0))
            self._fill_color = Color(self.tone[0], self.tone[1], self.tone[2], 0.115)
            self._panel = RoundedRectangle(
                pos=(-self.width / 2, -self.height / 2),
                size=self.size,
                radius=[dp(17)],
            )
            self._icon_color = Color(1, 1, 1, 0.52)
            self._icon_rects = [
                Rectangle(texture=texture) for texture in self._icon_textures
            ]
            self._edge_color = Color(1, 1, 1, 0.13)
            self._edge = Line(
                rounded_rectangle=(
                    -self.width / 2,
                    -self.height / 2,
                    self.width,
                    self.height,
                    dp(17),
                ),
                width=0.85,
            )
            self._stripe_color = Color(self.tone[0], self.tone[1], self.tone[2], 0.33)
            self._stripe = RoundedRectangle(
                pos=(-self.width * 0.31, -self.height * 0.27),
                size=(self.width * 0.38, dp(3)),
                radius=[dp(2)],
            )
            PopMatrix()
        self.bind(
            pos=self._sync_canvas,
            size=self._sync_canvas,
            angle=self._sync_canvas,
        )
        self._sync_canvas()

    def _sync_canvas(self, *_):
        self._translation.x = self.center_x
        self._translation.y = self.center_y
        self._rotation.angle = self.angle
        self._panel.pos = (-self.width / 2, -self.height / 2)
        self._panel.size = self.size
        self._edge.rounded_rectangle = (
            -self.width / 2,
            -self.height / 2,
            self.width,
            self.height,
            dp(17),
        )
        if len(self._icon_rects) == 1:
            icon_side = min(self.width * 0.62, self.height * 0.78)
            self._icon_rects[0].pos = (-icon_side / 2, -icon_side / 2 + dp(3))
            self._icon_rects[0].size = (icon_side, icon_side)
        else:
            icon_side = min(self.width * 0.47, self.height * 0.70)
            self._icon_rects[0].pos = (-self.width * 0.40, -icon_side / 2 + dp(3))
            self._icon_rects[0].size = (icon_side, icon_side)
            self._icon_rects[1].pos = (
                self.width * 0.40 - icon_side,
                -icon_side / 2 + dp(3),
            )
            self._icon_rects[1].size = (icon_side, icon_side)
        self._stripe.pos = (-self.width * 0.31, -self.height * 0.27)
        self._stripe.size = (self.width * 0.38, dp(3))


class AnimatedMenuBackdrop(FloatLayout):
    """Soft drifting color layers that stay cheap enough for mobile GPUs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(MenuGradientBackground())
        tile_specs = (
            (-0.02, 0.84, 15, 11, 0.1, -18, CYAN, (138, 84), ("rock", "scissors")),
            (0.91, 0.91, 12, 16, 1.7, 22, CORAL, (118, 72), ("paper",)),
            (1.03, 0.56, 18, 10, 3.4, -28, GOLD, (150, 92), ("paper", "rock")),
            (-0.08, 0.38, 13, 18, 4.8, 19, VIOLET, (130, 78), ("scissors",)),
            (0.90, 0.16, 17, 12, 2.6, -14, CYAN, (160, 94), ("rock", "paper")),
            (0.12, 0.06, 11, 14, 5.7, 27, CORAL, (102, 64), ("scissors", "rock")),
        )
        self.tiles = []
        for (
            base_x,
            base_y,
            drift_x,
            drift_y,
            phase,
            base_angle,
            tone,
            tile_size,
            gestures,
        ) in tile_specs:
            tile = AmbientTile(
                base_x=base_x,
                base_y=base_y,
                drift_x=dp(drift_x),
                drift_y=dp(drift_y),
                phase=phase,
                base_angle=base_angle,
                tone=tone,
                gestures=gestures,
                size_hint=(None, None),
                size=(dp(tile_size[0]), dp(tile_size[1])),
            )
            self.tiles.append(tile)
            self.add_widget(tile)
        self.bind(pos=lambda *_: self.step(0), size=lambda *_: self.step(0))

    def step(self, elapsed):
        for index, tile in enumerate(self.tiles):
            speed = 0.40 + index * 0.035
            tile.center_x = (
                self.x
                + self.width * tile.base_x
                + math.sin(elapsed * speed + tile.phase) * tile.drift_x
            )
            tile.center_y = (
                self.y
                + self.height * tile.base_y
                + math.cos(elapsed * (speed * 0.82) + tile.phase) * tile.drift_y
            )
            tile.angle = tile.base_angle + math.sin(elapsed * 0.28 + tile.phase) * 7


class MenuGestureItem(FloatLayout):
    """One locked hero column: hand and matching word share one center."""

    gesture = StringProperty("rock")
    title = StringProperty("ROCK")
    sprite_sheet = StringProperty("")
    accent = ListProperty(CYAN)
    sprite_scale = NumericProperty(0.8)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hand = SpriteGloveHand(
            gesture=self.gesture,
            sprite_sheet=self.sprite_sheet,
            hand_scale=self.sprite_scale,
            size_hint=(None, None),
        )
        self.add_widget(self.hand)
        self.caption = make_label(
            self.title,
            15,
            self.accent,
            True,
            size_hint=(None, None),
        )
        self.caption.bind(
            size=lambda widget, value: setattr(widget, "text_size", value)
        )
        self.add_widget(self.caption)
        self.bind(pos=self._layout_content, size=self._layout_content)
        self.bind(pos=self.redraw, size=self.redraw, accent=self.redraw)
        self._layout_content()
        self.redraw()

    def _layout_content(self, *_):
        caption_height = dp(34)
        self.hand.pos = (self.x, self.y + caption_height)
        self.hand.size = (self.width, max(0, self.height - caption_height))
        self.caption.pos = (self.x, self.y)
        self.caption.size = (self.width, caption_height)

    def redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(self.accent[0], self.accent[1], self.accent[2], 0.105)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
            Color(1, 1, 1, 0.10)
            Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(20)),
                width=0.85,
            )
            Color(self.accent[0], self.accent[1], self.accent[2], 0.72)
            RoundedRectangle(
                pos=(self.center_x - dp(14), self.y + dp(7)),
                size=(dp(28), dp(3)),
                radius=[dp(2)],
            )


class ModeScreen(FloatLayout):
    def __init__(self, on_start, on_settings, **kwargs):
        super().__init__(**kwargs)
        self.on_start = on_start
        self._menu_event = None
        self._menu_elapsed = 0.0
        self.backdrop = AnimatedMenuBackdrop()
        self.add_widget(self.backdrop)
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(22), dp(26), dp(22), dp(20)],
            spacing=dp(10),
        )
        self.add_widget(content)

        top_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        brand = make_label(
            "[color=9BE7DD]NEON[/color] [color=FFF8EC]HANDS[/color]",
            15,
            WHITE,
            True,
            markup=True,
        )
        brand.halign = "left"
        brand.bind(size=lambda widget, value: setattr(widget, "text_size", value))
        top_bar.add_widget(brand)
        settings = CardButton(
            text="SETTINGS",
            font_size="11sp",
            accent=GOLD,
            size_hint=(None, None),
            size=(dp(88), dp(42)),
        )
        settings.bind(on_release=lambda *_: on_settings())
        top_bar.add_widget(settings)
        content.add_widget(top_bar)

        content.add_widget(Widget(size_hint_y=0.08))
        content.add_widget(
            make_label(
                "[color=FFF7E9]HANDS READY![/color]\n"
                "[color=80D7CD]YOUR[/color] [color=F2B778]MOVE[/color]",
                28,
                WHITE,
                True,
                size_hint_y=None,
                height=dp(82),
                markup=True,
                line_height=0.90,
            )
        )

        gesture_row = BoxLayout(size_hint_y=None, height=dp(164), spacing=dp(8))
        self.hero_items = []
        gesture_data = (
            ("rock", "ROCK", CYAN, 0.91),
            ("paper", "PAPER", VIOLET, 0.75),
            ("scissors", "SCISSORS", CORAL, 0.75),
        )
        for gesture, title, accent, scale in gesture_data:
            item = MenuGestureItem(
                gesture=gesture,
                title=title,
                sprite_sheet=PLAYER_SHEET_PATH,
                accent=accent,
                sprite_scale=scale,
            )
            self.hero_items.append(item)
            gesture_row.add_widget(item)
        content.add_widget(gesture_row)

        content.add_widget(
            make_label(
                "Rock, paper, or scissors... Make your move.",
                14,
                (0.84, 0.85, 0.88, 1),
                size_hint_y=None,
                height=dp(36),
            )
        )
        content.add_widget(Widget(size_hint_y=0.16))

        match = PillButton(
            text="PLAY  •  FIRST TO 3",
            font_size="16sp",
            accent=(0.57, 0.45, 0.83, 1),
            size_hint_y=None,
            height=dp(72),
        )
        match.bind(on_release=lambda *_: self.on_start(3))
        content.add_widget(match)

        quick = CardButton(
            text="QUICK MATCH  •  ONE ROUND",
            font_size="14sp",
            accent=CYAN,
            size_hint_y=None,
            height=dp(62),
        )
        quick.bind(on_release=lambda *_: self.on_start(1))
        content.add_widget(quick)
        content.add_widget(Widget(size_hint_y=0.16))
        content.add_widget(
            make_label(
                "OFFLINE   •   NO ADS   •   INSTANT PLAY",
                10,
                (0.73, 0.78, 0.82, 1),
                True,
                size_hint_y=None,
                height=dp(28),
            )
        )

    def _animate_menu(self, dt):
        self._menu_elapsed += dt
        self.backdrop.step(self._menu_elapsed)
        for index, item in enumerate(self.hero_items):
            phase = index * 1.65
            item.hand.motion_y = dp(3.2) * math.sin(self._menu_elapsed * 1.35 + phase)
            item.hand.hand_angle = 1.4 * math.sin(self._menu_elapsed * 0.78 + phase)

    def on_parent(self, _, parent):
        if parent is not None and self._menu_event is None:
            self._menu_event = Clock.schedule_interval(self._animate_menu, 1 / 30)
        elif parent is None and self._menu_event is not None:
            self._menu_event.cancel()
            self._menu_event = None


class RPSApp(App):
    # Use one brand icon for Android and the desktop window title bar.
    icon = os.path.join(ASSET_DIRECTORY, "icon.png")

    def build(self):
        self.title = "Neon Hands — Rock Paper Scissors"
        verify_bundled_assets(ASSET_DIRECTORY)
        settings_path = os.path.join(self.user_data_dir, "settings.json")
        try:
            if os.path.isfile(settings_path) and os.path.getsize(settings_path) > 65536:
                raise ValueError("Settings file is unexpectedly large.")
            self.settings_store = JsonStore(settings_path)
        except (OSError, TypeError, ValueError):
            # Read-only or malformed settings must not prevent startup.
            self.settings_store = DictStore({})
        self.audio = AudioManager(ASSET_DIRECTORY, self.settings_store)
        self.root_layer = FloatLayout()
        self.show_menu()
        Clock.schedule_once(self.audio.start_music, 0.2)
        return self.root_layer

    def _replace(self, screen):
        old = self.root_layer.children[0] if self.root_layer.children else None
        screen.opacity = 0
        self.root_layer.add_widget(screen)
        Animation(opacity=1, duration=0.25, t="out_quad").start(screen)
        if old:
            animation = Animation(opacity=0, duration=0.18)
            animation.bind(
                on_complete=lambda *_: (
                    self.root_layer.remove_widget(old)
                    if old.parent is self.root_layer
                    else None
                )
            )
            animation.start(old)

    def show_menu(self):
        self.audio.switch_music("menu")
        self._replace(
            ModeScreen(
                on_start=self.start_game,
                on_settings=self.show_settings,
            )
        )

    def show_settings(self):
        if any(
            isinstance(child, SettingsOverlay) for child in self.root_layer.children
        ):
            return
        overlay = SettingsOverlay(
            audio=self.audio,
            on_close=self.close_settings,
        )
        overlay.opacity = 0
        self.root_layer.add_widget(overlay)
        Animation(opacity=1, duration=0.18, t="out_quad").start(overlay)

    def close_settings(self, overlay):
        animation = Animation(opacity=0, duration=0.15, t="out_quad")
        animation.bind(
            on_complete=lambda *_: (
                self.root_layer.remove_widget(overlay)
                if overlay.parent is self.root_layer
                else None
            )
        )
        animation.start(overlay)

    def start_game(self, target_score):
        self.audio.switch_music("battle")
        self._replace(GameScreen(target_score=target_score, on_menu=self.show_menu))

    def on_pause(self):
        self.audio.stop_music()
        return True

    def on_resume(self):
        self.audio.start_music()

    def on_stop(self):
        self.audio.stop_music()


if __name__ == "__main__":
    RPSApp().run()
