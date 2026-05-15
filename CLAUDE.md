# 酷和弦 (Cool Chord) - EDM Chord Synthesizer

## CRITICAL: Working Directory
ALL file paths MUST use `D:\编程\2 fantastic chord\`. Never use `D:\プログラミング\2 fantastic chord\`.
Before any write/edit operation, verify the path contains `编程` not `プログラミング`.
If you accidentally write to `D:\プログラミング`, immediately move files and delete that directory.

## Current State (2026-05-15)
- **Phase**: 1-12 全部完成
- **Source files**: 53
- **Tests**: 221 (26 test files)
- **Quality gates**: black / ruff / mypy strict — all pass

## Overview
A Python desktop synthesizer for EDM chord generation. Combines a real-time
synthesizer engine with automated chord progression generation across multiple
EDM styles, plus an intelligent drum machine with step sequencer, effects mixer,
and WAV/MIDI export.

## Tech Stack
- Python 3.11 (virtual env at .venv)
- Audio: sounddevice + numpy (real-time callback-based DSP)
- GUI: PySide6 (QGraphicsView piano roll, custom widget keyboard, knobs)
- MIDI: mido + python-rtmidi
- Music Theory: music21
- Export: soundfile

## Key Architecture
- Multi-threaded: GUI (PySide6 main), Audio (sounddevice callback), MIDI (rtmidi)
- Thread-safe communication via queue.Queue
- Block-based DSP in numpy (BLOCK_SIZE=512, SAMPLE_RATE=44100)
- All DSP operates on float32 numpy arrays
- Audio thread must NEVER block, allocate, or hold locks
- Drum voices: pre-rendered synthesis, slice-based playback in callback
- PianoRollSequencer: scans Pattern notes in audio callback, triggers voice allocation directly

## Commands
- Activate venv: `source .venv/Scripts/activate` (bash)
- Run: `python src/main.py`
- Test: `python -m pytest tests/ -x`
- Format: `black --line-length 120 src/ tests/`
- Lint: `ruff check src/ tests/`
- Type check: `mypy src/`
- All checks: `black --check src/ tests/ && ruff check src/ tests/ && mypy src/`

## Coding Standards
- PEP 8 via Black (120 char line, Python 3.11 target)
- Type hints REQUIRED everywhere (mypy strict)
- Module docstrings only - no excessive comments
- All synthesis local, no cloud APIs, offline-first
- `from __future__ import annotations` in all source files

## Directory Structure
src/audio/       - DSP engine (oscillators, filters, envelopes, effects, drum_synth, voices)
src/midi/        - MIDI I/O (real-time handler, file read/write, events)
src/chord/       - Chord & drum generation engine (theory, styles, generator, voicing)
src/sequencer/   - Piano roll model, drum patterns/sequencer, piano_roll_sequencer, transport
src/ui/          - PySide6 GUI (main_window, piano_roll, keyboard, synth_panel, drum_panel, chord_panel, effects_panel, step_sequencer, drum_pad, knob, transport, waveform)
src/export/      - WAV export (stereo + stems), MIDI export (piano_roll/drums/project)
src/utils/       - Configuration, logging, resource paths
resources/       - Style definitions (JSON, 10 EDM styles), drum kit presets, factory presets
tests/           - pytest test suite (26 files, 221 tests)
