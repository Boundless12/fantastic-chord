"""Wavetable generation and loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import numpy.typing as npt


def generate_sine_table(size: int = 2048) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    return np.sin(phases).astype(np.float32)


def generate_saw_table(size: int = 2048, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float32)
    for k in range(1, harmonics + 1):
        result += np.sin(k * phases) / k
    result = result / np.float32(np.max(np.abs(result)))
    return np.asarray(result, dtype=np.float32)


def generate_square_table(size: int = 2048, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float32)
    for k in range(1, harmonics + 1):
        if k % 2 == 1:
            result += np.sin(k * phases) / k
    result = result / np.float32(np.max(np.abs(result)))
    return np.asarray(result, dtype=np.float32)


def generate_triangle_table(size: int = 2048, harmonics: int = 64) -> npt.NDArray[np.float32]:
    phases = np.linspace(0, 2.0 * np.pi, size, endpoint=False, dtype=np.float32)
    result = np.zeros(size, dtype=np.float32)
    for k in range(1, harmonics + 1):
        if k % 2 == 1:
            sign = 1 if (k // 2) % 2 == 0 else -1
            result += sign * np.sin(k * phases) / (k * k)
    result = result / np.float32(np.max(np.abs(result)))
    return np.asarray(result, dtype=np.float32)


def generate_all_default_tables(size: int = 2048) -> None:
    """Generate and save default wavetable files to resources/wavetables/."""
    import os

    tables: dict[str, npt.NDArray[np.float32]] = {
        "sine_2048": generate_sine_table(size),
        "saw_2048": generate_saw_table(size),
        "square_2048": generate_square_table(size),
        "triangle_2048": generate_triangle_table(size),
    }

    base_dir = Path(__file__).parent.parent.parent / "resources" / "wavetables"
    os.makedirs(base_dir, exist_ok=True)

    for name, table in tables.items():
        path = base_dir / f"{name}.wt"
        with open(path, "w") as f:
            json.dump(table.tolist(), f)


def load_wavetable(path: str) -> npt.NDArray[np.float32]:
    """Load a .wt file (JSON array of float32 values)."""
    with open(path) as f:
        data = json.load(f)
    return np.array(data, dtype=np.float32)
