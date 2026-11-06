# AI Agent Installation & Discovery Guide for HyperEdit Pro

This document defines exact, tested instructions for installing and running **HyperEdit Pro** across leading AI agent platforms.

---

## 1. Supported Agent Environments

| Agent Platform | Discovery Mechanism | Global Path | Workspace Path |
| :--- | :--- | :--- | :--- |
| **OpenAI Codex** | Agent Skills standard (`SKILL.md`) | `~/.codex/skills/hyperedit-pro/` or `~/.agents/skills/` | `<workspace>/.codex/skills/hyperedit-pro/` or `<workspace>/SKILL.md` |
| **Claude Code** | Agent Skills (`SKILL.md`) & CLI tools | `~/.claude/skills/hyperedit-pro/` or `~/.agents/skills/` | `<workspace>/.claude/skills/hyperedit-pro/` or `<workspace>/SKILL.md` |
| **Cursor** | `.cursorrules` / `.cursor/skills/` | `~/.cursor/skills/hyperedit-pro/` | `<workspace>/.cursor/skills/hyperedit-pro/` or `<workspace>/SKILL.md` |
| **Gemini CLI / Antigravity** | Agent Skills engine (`SKILL.md`) | `~/.gemini/antigravity/skills/hyperedit-pro/` or `~/.agents/skills/` | `<workspace>/.agents/skills/hyperedit-pro/` or `<workspace>/SKILL.md` |

---

## 2. Automated One-Command Installation

HyperEdit Pro includes an automated multi-agent installer script:

```bash
# Clone the repository
git clone https://github.com/vexoralabsmx-source/HyperEdit-Pro.git
cd HyperEdit-Pro

# Install the Python package in editable mode
pip install -e ".[vision]"

# Install the Agent Skill into all detected agents in your current workspace
python scripts/install_skill.py --agent all --workspace .

# Or install globally into your home directory for all agent sessions:
python scripts/install_skill.py --agent all --global
```

---

## 3. Platform-Specific Setup

### 3.1 OpenAI Codex
Codex discovers skills by reading `SKILL.md` files containing standard YAML frontmatter:
```bash
# Install specifically for Codex in the current repository:
python scripts/install_skill.py --agent codex --workspace .
```
When prompting Codex:
> *"Use HyperEdit Pro to trim footage.mp4 from 00:00:02 to 00:00:15, normalize audio to YouTube -14 LUFS, and export to 1080p."*

Codex will automatically read `SKILL.md`, execute `hyperedit doctor` to verify FFmpeg, and run the corresponding `hyperedit timeline` and `hyperedit render` CLI commands.

---

### 3.2 Claude Code
Claude Code reads tools and skills from `.claude/skills/` and global configurations:
```bash
# Install for Claude Code:
python scripts/install_skill.py --agent claude --workspace .
```
Claude Code will immediately register `hyperedit` as an executable bash tool.

---

### 3.3 Cursor
Cursor indexes skills located in `.cursor/skills/` or referenced in `.cursorrules`:
```bash
# Install for Cursor:
python scripts/install_skill.py --agent cursor --workspace .
```
You can also reference HyperEdit Pro directly in your project's `.cursorrules` or `.cursor/rules/hyperedit.mdc`.

---

### 3.4 Gemini CLI / Google Antigravity
Google Antigravity natively loads skills from `~/.agents/skills/` or `~/.gemini/antigravity/skills/`:
```bash
# Install globally for Antigravity:
python scripts/install_skill.py --agent gemini --global
```
Once installed, the `/hyperedit` skill is instantly active and available across all conversation turns.

---

## 4. Environment Verification

After installation, verify that the agent's environment has all required multimedia binaries:
```bash
hyperedit doctor --json
```

Ensure that:
1. `ffmpeg` $\ge 5.0$ and `ffprobe` $\ge 5.0$ are installed and discoverable in `PATH`.
2. Python $\ge 3.11$ is active.
3. OpenCV (`opencv-python`) is installed if motion tracking, stabilization, or chroma keying is needed (`pip install -e ".[vision]"`).

