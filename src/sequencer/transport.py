"""Transport: Playback transport state machine."""


class Transport:
    """Playback transport with BPM, position, and loop support."""

    bpm: float
    time_signature: tuple[int, int]
    position_beats: float
    is_playing: bool
    is_recording: bool
    loop_start: float | None
    loop_end: float | None

    def __init__(self) -> None:
        self.bpm = 120.0
        self.time_signature = (4, 4)
        self.position_beats = 0.0
        self.is_playing = False
        self.is_recording = False
        self.loop_start = None
        self.loop_end = None

    def advance(self, frames: int, sample_rate: int) -> None:
        """Advance position by the given number of frames."""
        if not self.is_playing:
            return
        beats_per_second = self.bpm / 60.0
        beat_increment = frames / sample_rate * beats_per_second
        self.position_beats += beat_increment

        if self.loop_end is not None and self.position_beats >= self.loop_end:
            if self.loop_start is not None:
                self.position_beats = self.loop_start
            else:
                self.position_beats = 0.0

    def reset(self) -> None:
        self.position_beats = 0.0

    def set_bpm(self, bpm: float) -> None:
        self.bpm = max(20.0, min(999.0, bpm))

    def get_bar_beat(self) -> tuple[int, int]:
        """Return current (bar, beat) for display."""
        beats_per_bar = self.time_signature[0]
        total_beats = int(self.position_beats)
        bar = total_beats // beats_per_bar + 1
        beat = (total_beats % beats_per_bar) + 1
        return bar, beat

    @property
    def beat_in_bar(self) -> int:
        return int(self.position_beats) % self.time_signature[0]
