# Getting Started with HyperEdit Pro

## 1. System Requirements

- **Python**: 3.11, 3.12, or 3.13.
- **FFmpeg & FFprobe**: Version 6.0+ (FFmpeg 7.0+ or 9.0+ strongly recommended).
- **Node.js**: (Optional) For HyperFrames motion graphics rendering.

---

## 2. Installation

Install the package in editable mode:

```bash
cd "path/to/hyperedit pro"
pip install -e .
```

To include optional AI scene detection and speech recognition dependencies:

```bash
pip install -e ".[ai,vision]"
```

---

## 3. Environment Verification

Run `hyperedit doctor` to ensure your system has all required binaries and hardware acceleration encoders:

```bash
hyperedit doctor --verbose
```

---

## 4. Creating Your First Project

Create a new project using the `1080p` horizontal preset:

```bash
hyperedit new my_first_edit.json --preset 1080p --fps 30.0
```

Validate the created project file:

```bash
hyperedit validate my_first_edit.json
```

