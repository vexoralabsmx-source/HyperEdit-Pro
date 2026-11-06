# Contributing to HyperEdit Pro

Thank you for contributing to HyperEdit Pro. We maintain high engineering standards for deterministic audiovisual processing, clean code architecture, and autonomous AI agent compatibility.

---

## 1. Development Setup

### Prerequisites
- Python 3.11+
- FFmpeg 6.0+ (FFmpeg 7.0+ / 9.0+ recommended with `libass` and hardware encoders)
- Node.js 18+ (optional, for HyperFrames integration)

### Installation
Clone the repository and install in editable development mode:
```bash
git clone https://github.com/vexoralabsmx-source/HyperEdit-Pro.git
cd HyperEdit-Pro
pip install -e ".[dev]"
```

Verify your environment by running:
```bash
hyperedit doctor --verbose
```

---

## 2. Code Quality & Standards

1. **Strict Type Annotations**: All functions, methods, and public interfaces must have complete type annotations checked via `mypy`.
2. **Linting and Formatting**: Follow PEP 8 and modern Python conventions via `ruff`.
3. **No Fake Stubs or Simulated Returns**: Never create functions that simulate capabilities with hardcoded fake responses.
4. **Pydantic v2 Models**: All project formats and configurations must validate through Pydantic v2 schemas.
5. **Discrete Frame Math**: Always use `Timecode` or discrete integer frames when doing temporal math on timelines. Never do raw floating-point second math for clip boundaries.

---

## 3. Running Tests

Run the full test suite with pytest:
```bash
pytest -v
```

Run test suite with coverage report:
```bash
pytest --cov=hyperedit tests/
```

Run linter:
```bash
ruff check .
```

Run type checker:
```bash
mypy src/hyperedit
```

---

## 4. Pull Request Guidelines

- Ensure all existing and new tests pass.
- Write tests for any new CLI commands, model modifications, or filtergraph compilers.
- Update `ROADMAP.md` and documentation accordingly.

