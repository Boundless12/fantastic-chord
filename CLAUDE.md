# 酷和弦 (Cool Chord) - EDM Chord Synthesizer

## CRITICAL: Working Directory
ALL file paths MUST use `D:\编程\2 fantastic chord\` (Chinese 编程, NOT Japanese プログラミング).
Never use `D:\プログラミング\2 fantastic chord\` — this path does NOT exist and will cause errors.
Before any Read/Write/Edit/Bash operation, double-check: the directory is `编程` (2 chars 编+程), NOT `プログラミング` (6 katakana chars).
Common mistake: typing `プログラミング` (programming in katakana) instead of `编程` (Chinese).
If you accidentally try `D:\プログラミング`, immediately retry with `D:\编程`.

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

## Auto-Approval Rules
- After making code changes, ALWAYS run: `python -m pytest tests/ -x && ruff check src/ tests/ && mypy src/`
- Do NOT ask for permission before running tests, lints, or quality checks
- Do NOT ask for permission before running `python src/main.py`
- Do NOT ask "Do you want me to run tests?" — just run them automatically
- When the user says "打开程序" or "运行程序", just launch it immediately without asking
- When the user says "继续下一步", immediately figure out the next logical step and do it
- After any file edit, immediately proceed to the next task without waiting for confirmation
- Use Bash for operations when possible to avoid path errors
- NEVER use the path `D:\プログラミング\2 fantastic chord\` — always use `D:\编程\2 fantastic chord\`
- If you accidentally type `プログラミング` in a path, immediately correct it to `编程` before executing

## Directory Structure
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
