---
name: skilldoc
description: Skill health checker for OpenClaw — validates dependencies, reports broken skills, gives fix hints.
version: 1.1.0
author: chhotu2601
metadata:
  openclaw:
    os: [darwin, linux]
    requires:
      bins: [python3]
---

# skilldoc — Skill Doctor for OpenClaw

Scans all installed OpenClaw skills, validates their dependencies (binaries, OS requirements), and reports which skills are healthy, broken, or missing dependencies.

## Usage

```bash
# Full health check
python3 skilldoc.py check

# Verbose (show healthy skills too)
python3 skilldoc.py check -v

# JSON output (for cron/heartbeat integration)
python3 skilldoc.py check --json

# List all skills with status
python3 skilldoc.py list

# Get fix commands for broken skills
python3 skilldoc.py fix-hints

# Check a specific skill
python3 skilldoc.py check --skill discord-voice

# Add extra skill directories
python3 skilldoc.py check --dirs ~/clawd/skills/ /other/path/
```

## Features

- Scans builtin + custom skill directories automatically
- Auto-detects skill paths from `~/.openclaw/openclaw.json` config
- Validates required binaries via `which` checks
- OS compatibility checking
- Install hints from skill frontmatter metadata
- JSON output for automation (cron jobs, heartbeat checks)
- Works with or without PyYAML (graceful fallback parser)

## Integration

### Heartbeat check
```bash
python3 skilldoc.py check --json > /tmp/skilldoc-report.json
```
Parse JSON and alert on newly broken skills.

### Cron job
Schedule periodic scans to catch breakage after updates.

## Skill Dependency Declaration

For skilldoc to validate your skill's dependencies, add this to your SKILL.md frontmatter:

```yaml
---
metadata:
  openclaw:
    os: [darwin, linux]
    requires:
      bins: [ffmpeg, yt-dlp]
    install:
      - kind: brew
        formula: ffmpeg
      - kind: pip
        package: yt-dlp
---
```
