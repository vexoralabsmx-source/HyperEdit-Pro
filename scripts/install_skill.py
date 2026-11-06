"""Automated installer for HyperEdit Pro across AI agent environments (Codex, Claude Code, Cursor, Gemini CLI)."""

import argparse
import os
from pathlib import Path
import shutil
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_FILE = REPO_ROOT / "SKILL.md"


def get_agent_skill_paths(target_agent: str, is_global: bool, workspace: Path) -> list[Path]:
    """Resolve target skill destinations based on real agent standards."""
    user_home = Path.home()
    destinations: list[Path] = []

    if target_agent in ("codex", "all"):
        if is_global:
            destinations.append(user_home / ".codex" / "skills" / "hyperedit-pro")
            destinations.append(user_home / ".agents" / "skills" / "hyperedit-pro")
        else:
            destinations.append(workspace / ".codex" / "skills" / "hyperedit-pro")
            destinations.append(workspace / ".agents" / "skills" / "hyperedit-pro")

    if target_agent in ("claude", "all"):
        if is_global:
            destinations.append(user_home / ".claude" / "skills" / "hyperedit-pro")
        else:
            destinations.append(workspace / ".claude" / "skills" / "hyperedit-pro")

    if target_agent in ("cursor", "all"):
        if is_global:
            destinations.append(user_home / ".cursor" / "skills" / "hyperedit-pro")
        else:
            destinations.append(workspace / ".cursor" / "skills" / "hyperedit-pro")

    if target_agent in ("gemini", "antigravity", "all"):
        if is_global:
            destinations.append(user_home / ".gemini" / "antigravity" / "skills" / "hyperedit-pro")
            destinations.append(user_home / ".agents" / "skills" / "hyperedit-pro")
        else:
            destinations.append(workspace / ".agents" / "skills" / "hyperedit-pro")

    return destinations


def install_skill(target_agent: str, is_global: bool, workspace: Path) -> None:
    """Install SKILL.md into agent discovery locations."""
    if not SKILL_FILE.is_file():
        print(f"Error: {SKILL_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    destinations = get_agent_skill_paths(target_agent, is_global, workspace)
    installed_count = 0

    print(f"Installing HyperEdit Pro Agent Skill (Agent: {target_agent}, Global: {is_global})...")

    for dest in destinations:
        dest.mkdir(parents=True, exist_ok=True)
        target_skill = dest / "SKILL.md"
        shutil.copy2(SKILL_FILE, target_skill)

        # Copy references directory for full contextual guidance
        ref_src = REPO_ROOT / "references"
        ref_dest = dest / "references"
        if ref_src.is_dir():
            if ref_dest.exists():
                shutil.rmtree(ref_dest)
            shutil.copytree(ref_src, ref_dest)

        print(f"  ✓ Installed to: {target_skill}")
        installed_count += 1

    print(f"\nSuccessfully installed HyperEdit Pro to {installed_count} destination(s).")
    print("Agents in those environments can now automatically discover and execute `hyperedit`.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Install HyperEdit Pro for AI agents.")
    parser.add_argument(
        "--agent",
        choices=["codex", "claude", "cursor", "gemini", "all"],
        default="all",
        help="Target AI agent environment (default: all)",
    )
    parser.add_argument(
        "--global",
        dest="is_global",
        action="store_true",
        help="Install globally into user home directory (~/)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=REPO_ROOT,
        help="Target project workspace root (default: current repository)",
    )

    args = parser.parse_args()
    install_skill(args.agent, args.is_global, args.workspace.resolve())

