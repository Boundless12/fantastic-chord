# Enforce Correct Working Directory

This skill MUST be used at the start of every coding session to prevent
accidentally writing files to wrong directories.

## Rule

ALL file operations (Write, Edit, Read, Bash, Glob, Grep) MUST use the
absolute path prefix:

```
D:\编程\2 fantastic chord\
```

## Common Wrong Paths to Avoid

- `D:\プログラミング\2 fantastic chord\` (katakana encoding — WRONG)
- Any path starting with `D:\プログラミング`

## Verification

Before any file write, verify the path contains `编程` not `プログラミング`.
If a file was accidentally written to `D:\プログラミング`, immediately:
1. Move it to `D:\编程\2 fantastic chord\<same-relative-path>`
2. Delete `D:\プログラミング\2 fantastic chord\` entirely
3. Use `rm -rf "D:/プログラミング/2 fantastic chord"` to clean up

## PWD Check

At session start, run:
```
pwd
```
Expected output: `/d/编程/2 fantastic chord`
