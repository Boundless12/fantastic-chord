# Add New Drum Kit

Use this skill when the user wants to add a new drum kit preset.

## Steps
1. Ask the user for:
   - Drum kit name and category/style
   - Desired sound characteristics for each drum element
   - Optional: WAV samples to include

2. Create a new JSON file at `resources/drum_kits/<kit_slug>.json`
   following the standard DrumKit schema:
   - Each drum sound has a `type` and `params` object
   - params vary by drum type (kick, snare, hh, clap, tom, crash, percussion)

3. If WAV samples are provided, copy them to
   `resources/drum_samples/<kit_slug>/`.

4. The DrumKit loader will pick up the new kit on next application start.
