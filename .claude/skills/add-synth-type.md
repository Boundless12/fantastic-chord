# Add New Synthesis Type

Use this skill when the user wants to add a new synthesis method
(e.g., granular, additive, physical modeling).

## Steps
1. Determine the synthesis type requirements.
2. Create new oscillator class in `src/audio/oscillator.py` inheriting from
   `Oscillator`.
3. Update `SynthVoice` to support routing through the new oscillator.
4. Update `Patch` dataclass if new parameters are needed.
5. Add corresponding wavetable generation to `src/audio/wavetable.py`
   if needed.
6. Add tests in `tests/test_audio/`.
