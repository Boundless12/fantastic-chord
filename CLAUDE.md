# 酷和弦 (Cool Chord) - EDM Chord Synthesizer

## CRITICAL: Working Directory
ALL file paths MUST use `D:\编程\2 fantastic chord\`. Never use `D:\プログラミング\2 fantastic chord\`.
Before any write/edit operation, verify the path uses `编程` not `プログラミング`.

## Overview
A Python desktop synthesizer for EDM chord generation. Combines a real-time
synthesizer engine with automated chord progression generation across multiple
EDM styles, plus an intelligent drum machine with step sequencer.

## Tech Stack
- Python 3.11 (virtual env at .venv)
- Audio: sounddevice + numpy (real-time callback-based DSP)
- GUI: PySide6 (QGraphicsView piano roll, custom widget keyboard)
- MIDI: mido + python-rtmidi
- Music Theory: music21
- Export: soundfile + scipy

## Key Architecture
- Multi-threaded: GUI (PySide6 main), Audio (sounddevice callback), MIDI (rtmidi)
- Thread-safe communication via queue.Queue
- Block-based DSP in numpy (BLOCK_SIZE=512, SAMPLE_RATE=44100)
- All DSP operates on float32 numpy arrays
- Audio thread must NEVER block, allocate, or hold locks
- Drum voices: pre-rendered synthesis, slice-based playback in callback

## Commands
- Activate venv: `source .venv/Scripts/activate` (bash)
- Run: `python src/main.py`
- Test: `pytest tests/`
- Format: `black --line-length 120 src/ tests/`
- Lint: `ruff check src/ tests/`
- Type check: `mypy src/`
- All checks: `black --check src/ tests/ && ruff check src/ tests/ && mypy src/`

## Coding Standards
- PEP 8 via Black (120 char line, Python 3.11 target)
- Type hints REQUIRED everywhere (mypy strict)
- Google-style docstrings for public API
- Module docstrings only - no excessive comments
- All synthesis local, no cloud APIs, offline-first

## Directory Structure
src/audio/       - DSP engine (oscillators, filters, envelopes, effects, drum_synth, voices)
src/midi/        - MIDI I/O (real-time handler, file read/write, events)
src/chord/       - Chord & drum generation engine (theory, styles, generator, voicing)
src/sequencer/   - Piano roll model, drum patterns, step sequencer, transport
src/ui/          - PySide6 GUI (main window, piano roll, keyboard, synth panel, drum panel)
src/export/      - WAV and MIDI export
src/utils/       - Configuration, logging, resource paths
resources/       - Style definitions (JSON), drum kits, wavetables, presets
tests/           - pytest test suite
