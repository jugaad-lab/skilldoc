# 🩺 skilldoc — Skill Doctor for OpenClaw

Validates all installed OpenClaw skills by checking their declared dependencies (binaries, OS requirements) and reports which are healthy, broken, or missing deps.

## The Problem

OpenClaw skills declare binary dependencies in their SKILL.md frontmatter, but there's no way to know which skills will actually work on your system until you try to use them and they fail. With 50+ skills installed, debugging "command not found" errors one at a time is painful.

## Usage

```bash
# Full health check (shows broken skills)
python3 skilldoc.py check

# Verbose — also show healthy skills  
python3 skilldoc.py check -v

# List all skills with status
python3 skilldoc.py list

# Get copy-pasteable fix commands
python3 skilldoc.py fix-hints

# Check a specific skill
python3 skilldoc.py check --skill apple-notes

# JSON output (for automation/heartbeats)
python3 skilldoc.py check --json

# Filter
python3 skilldoc.py check --filter broken
```

## Integration

### Heartbeat Check
Add to HEARTBEAT.md for periodic skill health monitoring:
```bash
python3 ~/workspace/agent-forge/2026-02-11-skilldoc/skilldoc.py check --json /tmp/skilldoc.json
```

### After `openclaw update`
Run `skilldoc check` after updates to see if new skills need dependencies installed.

## How It Works

1. Scans `/opt/homebrew/lib/node_modules/openclaw/skills/` (builtin) and `~/workspace/skills/` (custom)
2. Parses YAML frontmatter from each SKILL.md
3. Extracts `metadata.openclaw.requires.bins` and `metadata.openclaw.os`
4. Checks each binary with `which`
5. Reports status with install hints from `metadata.openclaw.install`

## Requirements

- Python 3.10+
- PyYAML (`pip install pyyaml`) — falls back to regex parsing if unavailable
