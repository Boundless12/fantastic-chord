"""Wavetable generation and loading utilities — Serum-style multi-table engine."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import numpy.typing as npt

TABLE_SIZE = 2048


def _normalize(table: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    peak = float(np.max(np.abs(table)))
    return np.asarray(table / max(peak, 1e-9), dtype=np.float32)


def generate_sine_table(size: int = TABLE_SIZE) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    return np.sin(phases).astype(np.float32)


def generate_saw_table(size: int = TABLE_SIZE, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float64)
    for k in range(1, harmonics + 1):
        result += np.sin(k * phases) / k
    return _normalize(result.astype(np.float32))


def generate_square_table(size: int = TABLE_SIZE, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float64)
    for k in range(1, harmonics + 1):
        if k % 2 == 1:
            result += np.sin(k * phases) / k
    return _normalize(result.astype(np.float32))


def generate_triangle_table(size: int = TABLE_SIZE, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float64)
    for k in range(1, harmonics + 1):
        if k % 2 == 1:
            sign = 1 if (k // 2) % 2 == 0 else -1
            result += sign * np.sin(k * phases) / (k * k)
    return _normalize(result.astype(np.float32))


def generate_pulse_table(size: int = TABLE_SIZE, harmonics: int = 32) -> npt.NDArray[np.float32]:
    """Generate a pulse wave with ~25% duty cycle."""
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float64)
    duty = 0.25
    for k in range(1, harmonics + 1):
        result += (np.sin(k * (phases - np.pi * duty)) - np.sin(k * (phases + np.pi * duty))) / k
    return _normalize(result.astype(np.float32))


def generate_wavetable_set(name: str, frame_count: int = 64, size: int = TABLE_SIZE) -> list[npt.NDArray[np.float32]]:
    """Generate a multi-frame Serum-style wavetable set.

    Args:
        name: One of 'analog_saw', 'digital_saw', 'jaws', 'pwm_square', 'sqr_saw',
              'wavetable_sweep', 'organ', 'vocal', 'tubes', 'growl'.
        frame_count: Number of frames (tables) in the set.
        size: Samples per single-cycle table.

    Returns:
        List of (frame_count,) float32 arrays, each of length size.
    """
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    frames: list[npt.NDArray[np.float32]] = []

    if name == "analog_saw":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            har = int(2 + t * 60)
            result = np.zeros(size, dtype=np.float64)
            for k in range(1, har + 1):
                result += np.sin(k * phases) / (k ** (1.0 + t * 0.05))
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "digital_saw":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            har = int(3 + t * 50)
            result = np.zeros(size, dtype=np.float64)
            for k in range(1, har + 1):
                amp = 1.0 / k * (1.0 + 0.3 * np.sin(k * t * np.pi))
                result += np.sin(k * phases) * amp
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "jaws":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            har = int(3 + t * 55)
            result = np.zeros(size, dtype=np.float64)
            for k in range(1, har + 1):
                amp = 1.0 / k if k % 2 == 1 else 0.3 / k
                phase_shift = t * np.pi * np.sin(k * 0.5)
                result += np.sin(k * phases + phase_shift) * amp
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "pwm_square":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            duty = 0.1 + t * 0.4  # 10% to 50%
            har = 32
            result = np.zeros(size, dtype=np.float64)
            for k in range(1, har + 1):
                if k % 2 == 1:
                    result += (np.sin(k * (phases - np.pi * duty)) - np.sin(k * (phases + np.pi * duty))) / k
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "sqr_saw":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            sqr = np.zeros(size, dtype=np.float64)
            saw = np.zeros(size, dtype=np.float64)
            har = 32
            for k in range(1, har + 1):
                if k % 2 == 1:
                    sqr += np.sin(k * phases) / k
                saw += np.sin(k * phases) / k
            sqr_norm = _normalize(sqr.astype(np.float32))
            saw_norm = _normalize(saw.astype(np.float32))
            blended = sqr_norm * (1.0 - t) + saw_norm * t
            frames.append(_normalize(blended))

    elif name == "wavetable_sweep":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            result = np.zeros(size, dtype=np.float64)
            har_count = int(3 + t * 60)
            for k in range(1, har_count + 1):
                phase_mod = t * 2.0 * np.sin(k * 1.7)
                amp = 1.0 / (k ** (0.8 + t * 0.3))
                result += np.sin(k * phases + phase_mod) * amp
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "organ":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            result = np.zeros(size, dtype=np.float64)
            # Mix of sine (drawbar 1: t=0) to fuller organ (t=1)
            drawbars = [
                1.0,  # 8'
                0.5 + t * 0.5,  # 4'
                0.0 + t * 0.5,  # 2 2/3'
                0.5 + t * 0.5,  # 2'
                0.0 + t * 0.3,  # 1 3/5'
                0.2 + t * 0.3,  # 1 1/3'
                0.0 + t * 0.2,  # 1'
            ]
            for j, amp in enumerate(drawbars):
                harmonic = 1 + j
                result += np.sin(harmonic * phases) * amp
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "vocal":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            # Formant-like: combine sine with phase-shifted second harmonic
            result = np.zeros(size, dtype=np.float64)
            f1 = 1.0
            f2 = 2.0 + t * 0.5
            f3 = 3.0 + t * 1.0
            result += np.sin(f1 * phases) * 1.0
            result += np.sin(f2 * phases - t) * (0.5 - t * 0.3)
            result += np.sin(f3 * phases + t * 2.0) * (0.3 + t * 0.3)
            frames.append(_normalize(result.astype(np.float32)))

    elif name == "tubes":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            saw = np.zeros(size, dtype=np.float64)
            har = 32
            for k in range(1, har + 1):
                saw += np.sin(k * phases) / k
            saw_norm = _normalize(saw.astype(np.float32))
            drive = 0.5 + t * 4.0
            distorted = np.tanh(saw_norm * drive)
            frames.append(_normalize(distorted.astype(np.float32)))

    elif name == "growl":
        for i in range(frame_count):
            t = i / (frame_count - 1)
            result = np.zeros(size, dtype=np.float64)
            fm_depth = t * 3.0
            mod_freq = 1.5 + t * 2.0
            for k in range(1, 20):
                amp = 1.0 / k
                mod = np.sin(mod_freq * k * phases) * fm_depth
                result += np.sin(k * phases + mod) * amp
            frames.append(_normalize(result.astype(np.float32)))

    else:
        # fallback: single sine frame
        frames.append(generate_sine_table(size))

    return frames


WAVETABLE_NAMES = [
    "analog_saw",
    "digital_saw",
    "jaws",
    "pwm_square",
    "sqr_saw",
    "wavetable_sweep",
    "organ",
    "vocal",
    "tubes",
    "growl",
]


def generate_all_default_tables(size: int = TABLE_SIZE) -> None:
    """Generate and save default wavetable files to resources/wavetables/."""
    import os

    base_dir = Path(__file__).parent.parent.parent / "resources" / "wavetables"
    os.makedirs(base_dir, exist_ok=True)

    # Single tables
    singles: dict[str, npt.NDArray[np.float32]] = {
        "sine_2048": generate_sine_table(size),
        "saw_2048": generate_saw_table(size),
        "square_2048": generate_square_table(size),
        "triangle_2048": generate_triangle_table(size),
    }
    for name, table in singles.items():
        path = base_dir / f"{name}.wt"
        with open(path, "w") as f:
            json.dump(table.tolist(), f)

    # Multi-table sets
    frame_count = 64
    for wt_name in WAVETABLE_NAMES:
        tables = generate_wavetable_set(wt_name, frame_count=frame_count, size=size)
        data = [t.tolist() for t in tables]
        path = base_dir / f"{wt_name}_{frame_count}.wt"
        with open(path, "w") as f:
            json.dump(data, f)


def load_wavetable(path: str) -> npt.NDArray[np.float32]:
    """Load a .wt file (JSON array of float32 values or nested array for multi-table)."""
    with open(path) as f:
        data = json.load(f)
    arr = np.array(data, dtype=np.float32)
    if arr.ndim == 2:
        return arr  # shape (frames, size)
    return arr  # shape (size,)
