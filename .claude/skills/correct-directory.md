# Enforce Correct Working Directory

## AUTO-TRIGGER: This skill activates whenever you type `プログラミング`

If you EVER find yourself typing `D:\プログラミング`, STOP IMMEDIATELY.
That is the WRONG directory. The correct directory is `D:\编程`.

## CRITICAL RULE

ALL file paths MUST use `D:\编程\2 fantastic chord\`

`编程` = Chinese (bian cheng) — CORRECT
`プログラミング` = Japanese katakana (puroguramingu) — WRONG

## Detection Pattern

If you type any of these, you must self-correct:
- `D:\プログラミング\` → CHANGE TO `D:\编程\`
- `D:/プログラミング/` → CHANGE TO `D:/编程/`
- Any path containing プログラミング → REPLACE with 编程

## Self-Check (Run Before EVERY Tool Call)

1. Look at the `file_path` parameter
2. Scan for the character sequence `プログラミング`
3. If found: STOP. Replace with `编程`. Re-issue the tool call.
4. Verify: the path must start with `D:\编程\`

## If You Already Made the Mistake

If a Write was done to `D:\プログラミング\...\file.py`:
```bash
mv "D:/プログラミング/2 fantastic chord/path/file.py" "D:/编程/2 fantastic chord/path/file.py"
```

If a directory tree exists at `D:\プログラミング\2 fantastic chord\`:
```bash
find "D:/プログラミング/2 fantastic chord/" -type f  # list leftovers
```

## Correct Path Examples

- `D:\编程\2 fantastic chord\src\ui\main_window.py`
- `D:\编程\2 fantastic chord\tests\test_audio\test_engine.py`
- `D:\编程\2 fantastic chord\.claude\settings.json`
