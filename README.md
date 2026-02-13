[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub Repo stars](https://img.shields.io/github/stars/jugaad-lab/skilldoc?style=social)](https://github.com/jugaad-lab/skilldoc/stargazers)

# 🩺 skilldoc — Skill Doctor for OpenClaw

Validates all installed OpenClaw skills by checking their declared dependencies (binaries, OS requirements) and reports which are healthy, broken, or missing deps.

> 📌 **If you find this useful, please ⭐ star this repo!** It helps other developers maintain healthy OpenClaw installations.

## Quick Install

```bash
# Clone and run
git clone https://github.com/jugaad-lab/skilldoc.git
cd skilldoc
pip install pyyaml  # optional but recommended
python3 skilldoc.py check
```

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
python3 ~/workspace/agent-forge/2026-02-11-skilldoc/skilldoc.py check --json
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

---
## More from Jugaad Lab 🔧
| Tool | What it does |
|------|-------------|
| [claude-code-mastery](https://github.com/jugaad-lab/claude-code-mastery) | Master Claude Code with subagents & automation |
| [tokenmeter](https://github.com/jugaad-lab/tokenmeter) | Track AI token usage & costs locally |
| [clawguard](https://github.com/jugaad-lab/clawguard) | Security blacklist for AI agents |
| [clawdscan](https://github.com/jugaad-lab/clawdscan) | Session health analyzer for OpenClaw |
| [skilldoc](https://github.com/jugaad-lab/skilldoc) | Skill health checker for OpenClaw |
| [tribe-protocol](https://github.com/jugaad-lab/tribe-protocol) | Trust & access control for AI bots |
| [discord-voice-plugin](https://github.com/jugaad-lab/discord-voice-plugin) | Voice conversations with AI in Discord |
| [worldmonitor](https://github.com/jugaad-lab/worldmonitor) | Real-time global intelligence dashboard |

⭐ **Found these useful? Star the repos you like!**
