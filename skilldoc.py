#!/usr/bin/env python3
"""skilldoc — Skill Doctor for OpenClaw

Scans all installed skills, validates dependencies (binaries, OS requirements),
and reports which skills are healthy, broken, or missing dependencies.
Optionally suggests install commands.
"""

import argparse
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
try:
    import yaml
except ImportError:
    yaml = None

# Default skill directories to scan
DEFAULT_SKILL_DIRS = [
    os.path.expanduser("/opt/homebrew/lib/node_modules/openclaw/skills"),
    os.path.expanduser("~/workspace/skills"),
]


def get_skill_dirs(extra_dirs=None):
    """Build skill directory list from OpenClaw config + defaults + extra dirs."""
    dirs = list(DEFAULT_SKILL_DIRS)

    # Try reading custom skill paths from OpenClaw config
    for config_path in [
        os.path.expanduser("~/.openclaw/openclaw.json"),
        os.path.expanduser("~/.clawdbot/clawdbot.json"),
    ]:
        try:
            with open(config_path) as f:
                config = json.load(f)
            # Check agents.defaults.skillDirs (actual OpenClaw schema)
            agents_cfg = config.get("agents", {}).get("defaults", {})
            skill_dirs_cfg = agents_cfg.get("skillDirs", [])
            if isinstance(skill_dirs_cfg, list):
                dirs.extend([os.path.expanduser(p) for p in skill_dirs_cfg])
            elif isinstance(skill_dirs_cfg, str):
                dirs.append(os.path.expanduser(skill_dirs_cfg))
            # Also check skills.dirs/paths as fallback
            skills_cfg = config.get("skills", {})
            if isinstance(skills_cfg, dict):
                for key in ("dirs", "paths", "directories"):
                    paths = skills_cfg.get(key, [])
                    if isinstance(paths, list):
                        dirs.extend([os.path.expanduser(p) for p in paths])
                    elif isinstance(paths, str):
                        dirs.append(os.path.expanduser(paths))
            break  # Use first config found
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            continue

    # Add extra dirs from CLI
    if extra_dirs:
        dirs.extend([os.path.expanduser(d) for d in extra_dirs])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for d in dirs:
        real = os.path.realpath(d)
        if real not in seen:
            seen.add(real)
            unique.append(d)
    return unique


# SKILL_DIRS removed — dirs are piped through function args

def parse_frontmatter(path):
    """Extract YAML frontmatter from SKILL.md."""
    try:
        with open(path) as f:
            content = f.read()
    except Exception:
        return None
    
    if not content.startswith("---"):
        return None
    
    end = content.find("---", 3)
    if end == -1:
        return None
    
    fm_text = content[3:end].strip()
    try:
        if yaml:
            return yaml.safe_load(fm_text)
        # Fallback: simple key-value parsing for common fields
        return _parse_simple_frontmatter(fm_text)
    except Exception:
        return _parse_simple_frontmatter(fm_text)

def _parse_simple_frontmatter(text):
    """Minimal frontmatter parser without PyYAML."""
    result = {}
    # Get simple key: value pairs
    for line in text.split("\n"):
        m = re.match(r'^(\w[\w-]*)\s*:\s*(.+)$', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            result[key] = val
    # Try to find JSON metadata block
    json_match = re.search(r'"openclaw"\s*:\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})', text)
    if json_match:
        try:
            oc = json.loads(json_match.group(1))
            if "metadata" not in result or not isinstance(result.get("metadata"), dict):
                result["metadata"] = {}
            result["metadata"]["openclaw"] = oc
        except json.JSONDecodeError:
            pass
    # Also try the full metadata block as JSON
    meta_match = re.search(r'metadata\s*:\s*\n\s*(\{[\s\S]*?\})\s*\n---', text + "\n---")
    if meta_match and (not isinstance(result.get("metadata"), dict)):
        try:
            result["metadata"] = json.loads(meta_match.group(1))
        except json.JSONDecodeError:
            pass
    return result if result else None

def extract_openclaw_meta(fm):
    """Extract openclaw metadata from frontmatter."""
    if not fm or not isinstance(fm, dict):
        return {}
    meta = fm.get("metadata", {})
    if isinstance(meta, dict):
        return meta.get("openclaw", {})
    return {}

def check_binary(name):
    """Check if a binary is available on PATH."""
    return shutil.which(name) is not None

def check_binary_version(name):
    """Try to get version of a binary."""
    try:
        result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
        out = (result.stdout or result.stderr or "").strip().split("\n")[0][:80]
        return out if out else None
    except Exception:
        return None

def scan_skills(skill_dirs=None):
    """Scan all skill directories and return skill info."""
    skills = []
    current_os = platform.system().lower()
    dirs = skill_dirs or DEFAULT_SKILL_DIRS
    
    for skill_dir in dirs:
        if not os.path.isdir(skill_dir):
            continue
        for skill_path in sorted(glob.glob(os.path.join(skill_dir, "*/SKILL.md"))):
            skill_name = os.path.basename(os.path.dirname(skill_path))
            source = "builtin" if "node_modules" in skill_path else "custom"
            
            fm = parse_frontmatter(skill_path)
            meta = extract_openclaw_meta(fm)
            
            skill = {
                "name": skill_name,
                "path": os.path.dirname(skill_path),
                "source": source,
                "description": fm.get("description", "") if fm else "",
                "os_req": meta.get("os", []),
                "required_bins": meta.get("requires", {}).get("bins", []) if meta else [],
                "install_info": meta.get("install", []) if meta else [],
                "bins_status": {},
                "os_ok": True,
                "healthy": True,
                "issues": [],
            }
            
            # Check OS compatibility
            if skill["os_req"]:
                os_map = {"darwin": "darwin", "linux": "linux", "win32": "windows"}
                if current_os not in [os_map.get(o, o) for o in skill["os_req"]]:
                    skill["os_ok"] = False
                    skill["healthy"] = False
                    skill["issues"].append(f"OS mismatch: needs {skill['os_req']}, have {current_os}")
            
            # Check required binaries
            for bin_name in skill["required_bins"]:
                found = check_binary(bin_name)
                skill["bins_status"][bin_name] = found
                if not found:
                    skill["healthy"] = False
                    skill["issues"].append(f"Missing binary: {bin_name}")
            
            skills.append(skill)
    
    return skills

def get_install_hint(skill):
    """Get install command hint for a skill."""
    hints = []
    for inst in skill.get("install_info", []):
        if isinstance(inst, dict):
            kind = inst.get("kind", "")
            if kind == "brew":
                formula = inst.get("formula", "")
                if formula:
                    hints.append(f"brew install {formula}")
            elif kind == "npm":
                pkg = inst.get("package", "")
                if pkg:
                    hints.append(f"npm install -g {pkg}")
            elif kind == "pip":
                pkg = inst.get("package", "")
                if pkg:
                    hints.append(f"pip install {pkg}")
            elif kind == "shell":
                cmd = inst.get("cmd", "")
                if cmd:
                    hints.append(cmd)
    return hints

def print_report(skills, verbose=False, json_out=False, filter_status=None):
    """Print the skill health report."""
    if filter_status == "healthy":
        skills = [s for s in skills if s["healthy"]]
    elif filter_status == "broken":
        skills = [s for s in skills if not s["healthy"]]
    
    if json_out:
        print(json.dumps(skills, indent=2))
        return
    
    healthy = [s for s in skills if s["healthy"]]
    broken = [s for s in skills if not s["healthy"]]
    no_deps = [s for s in skills if not s["required_bins"] and not s["os_req"]]
    
    print(f"\n🩺 Skill Doctor Report")
    print(f"{'='*60}")
    print(f"📦 Total skills scanned: {len(skills)}")
    print(f"✅ Healthy: {len(healthy)}")
    print(f"❌ Broken:  {len(broken)}")
    print(f"📝 No deps declared: {len(no_deps)}")
    print()
    
    if broken:
        print(f"❌ BROKEN SKILLS ({len(broken)})")
        print(f"{'-'*60}")
        for s in broken:
            print(f"\n  🔴 {s['name']} ({s['source']})")
            for issue in s["issues"]:
                print(f"     ⚠️  {issue}")
            hints = get_install_hint(s)
            if hints:
                for h in hints:
                    print(f"     💡 Fix: {h}")
        print()
    
    if verbose:
        print(f"✅ HEALTHY SKILLS ({len(healthy)})")
        print(f"{'-'*60}")
        for s in healthy:
            bins = ", ".join(s["required_bins"]) if s["required_bins"] else "none"
            print(f"  🟢 {s['name']} ({s['source']}) — bins: {bins}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Skill Doctor — validate OpenClaw skill dependencies")
    parser.add_argument("command", nargs="?", default="check", choices=["check", "list", "fix-hints"])
    parser.add_argument("-v", "--verbose", action="store_true", help="Show healthy skills too")
    parser.add_argument("--json", action="store_true", dest="json_out", help="JSON output")
    parser.add_argument("--filter", choices=["healthy", "broken"], help="Filter by status")
    parser.add_argument("--skill", help="Check a specific skill by name")
    parser.add_argument("--dirs", nargs="+", metavar="DIR", help="Additional skill directories to scan")
    args = parser.parse_args()
    
    skill_dirs = get_skill_dirs(extra_dirs=args.dirs)
    skills = scan_skills(skill_dirs)
    
    if args.skill:
        skills = [s for s in skills if s["name"] == args.skill]
        if not skills:
            print(f"Skill '{args.skill}' not found")
            sys.exit(1)
    
    if args.command == "check":
        print_report(skills, verbose=args.verbose, json_out=args.json_out, filter_status=args.filter)
    elif args.command == "list":
        for s in skills:
            status = "✅" if s["healthy"] else "❌"
            print(f"{status} {s['name']:30s} {s['source']:8s} bins={','.join(s['required_bins']) or 'none'}")
    elif args.command == "fix-hints":
        broken = [s for s in skills if not s["healthy"]]
        if not broken:
            print("All skills healthy! Nothing to fix.")
            return
        print("# Fix commands for broken skills:\n")
        for s in broken:
            hints = get_install_hint(s)
            if hints:
                print(f"# {s['name']}")
                for h in hints:
                    print(h)
                print()
            else:
                missing = [b for b, ok in s["bins_status"].items() if not ok]
                if missing:
                    print(f"# {s['name']} — no install info, missing: {', '.join(missing)}")
                    print()

if __name__ == "__main__":
    main()
