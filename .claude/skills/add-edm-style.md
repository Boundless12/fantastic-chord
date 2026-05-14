# Add New EDM Style

Use this skill when the user wants to add a new EDM chord style definition.

## Steps
1. Ask the user for:
   - Style name and description
   - Typical tempo range
   - Preferred scale types
   - Characteristic chord qualities
   - Common chord progressions
   - Drum pattern preferences

2. Create a new JSON file at `resources/styles/<style_slug>.json`
   following the standard schema (see existing style files for reference).

3. The style file must include: name, description, tempo_range,
   time_signatures, scale_degrees, common_progressions,
   rhythm_patterns, voicing, feel, drum_patterns, suggested_drum_kit.

4. After creating the file, the StyleManager will auto-load it on next
   application start.
