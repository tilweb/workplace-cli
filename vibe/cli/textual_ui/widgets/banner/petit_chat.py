from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.timer import Timer
from textual.widgets import Static

from vibe.cli.textual_ui.widgets.braille_renderer import render_braille

WIDTH = 22
HEIGHT = 12

# "KI" letters in dot coordinates (x values per row y)
# K: stem at x=1,2 with diagonals, I: bar at top/bottom with stem at x=16,17
STARTING_DOTS = [
    set(),                                          # y=0:  (animation zone for I spark)
    {1, 2, 8, 9, 14, 15, 16, 17, 18, 19},         # y=1:  K top + I top bar
    {1, 2, 7, 8, 16, 17},                          # y=2
    {1, 2, 5, 6, 16, 17},                          # y=3
    {1, 2, 4, 5, 16, 17},                          # y=4
    {1, 2, 3, 4, 16, 17},                          # y=5:  K junction
    {1, 2, 4, 5, 16, 17},                          # y=6
    {1, 2, 5, 6, 16, 17},                          # y=7
    {1, 2, 7, 8, 16, 17},                          # y=8
    {1, 2, 8, 9, 14, 15, 16, 17, 18, 19},         # y=9:  K bottom + I bottom bar
    set(),                                          # y=10: (animation zone for K kick)
    set(),                                          # y=11
]

# --- Animation transitions ---
WAIT = {"remove": set[int](), "add": set[int]()}

# I top: spark/pulse appears above I center (y=0)
I_SPARK_ON = {
    "remove": set[int](),
    "add": {0j + 16, 0j + 17},
}
I_SPARK_EXPAND = {
    "remove": set[int](),
    "add": {0j + 15, 0j + 18},
}
I_SPARK_CONTRACT = {
    "remove": {0j + 15, 0j + 18},
    "add": set[int](),
}
I_SPARK_OFF = {
    "remove": {0j + 16, 0j + 17},
    "add": set[int](),
}

# K bottom: diagonal legs extend outward at y=10
K_LEFT_KICK = {
    "remove": set[int](),
    "add": {10j + 0, 10j + 1},
}
K_RIGHT_KICK = {
    "remove": set[int](),
    "add": {10j + 9, 10j + 10},
}
K_LEFT_BACK = {
    "remove": {10j + 0, 10j + 1},
    "add": set[int](),
}
K_RIGHT_BACK = {
    "remove": {10j + 9, 10j + 10},
    "add": set[int](),
}

TRANSITIONS = [
    WAIT,
    I_SPARK_ON,        # dot appears above I
    WAIT,
    I_SPARK_EXPAND,    # spark widens
    WAIT,
    I_SPARK_CONTRACT,  # spark narrows
    I_SPARK_OFF,       # spark disappears
    WAIT,
    K_LEFT_KICK,       # K left leg extends down
    K_RIGHT_KICK,      # K right leg extends down
    WAIT,
    K_LEFT_BACK,       # left leg retracts
    K_RIGHT_BACK,      # right leg retracts
    WAIT,
    WAIT,
]


class PetitChat(Static):
    def __init__(self, animate: bool = True, **kwargs: Any) -> None:
        super().__init__(**kwargs, classes="banner-chat")
        self._dots = {1j * y + x for y, row in enumerate(STARTING_DOTS) for x in row}
        self._transition_index = 0
        self._do_animate = animate
        self._freeze_requested = False
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Static(render_braille(self._dots, WIDTH, HEIGHT), classes="petit-chat")

    def on_mount(self) -> None:
        self._inner = self.query_one(".petit-chat", Static)
        if self._do_animate:
            self._timer = self.set_interval(0.18, self._apply_next_transition)

    def freeze_animation(self) -> None:
        self._freeze_requested = True

    def _apply_next_transition(self) -> None:
        if self._freeze_requested and self._transition_index == 0:
            if self._timer:
                self._timer.stop()
            self._timer = None
            return

        transition = TRANSITIONS[self._transition_index]
        self._dots -= transition["remove"]
        self._dots |= transition["add"]
        self._transition_index = (self._transition_index + 1) % len(TRANSITIONS)
        self._inner.update(render_braille(self._dots, WIDTH, HEIGHT))
