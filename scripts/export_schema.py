#!/usr/bin/env python3
"""Exports the Pydantic Project model JSON Schema to assets/project.schema.json."""

import json
from pathlib import Path
import sys

root_dir = Path(__file__).resolve().parent.parent
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from hyperedit.core.models.project import Project  # noqa: E402


def export_schema() -> Path:
    schema = Project.model_json_schema()
    schema_path = root_dir / "assets" / "project.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"JSON Schema written to {schema_path}")
    return schema_path


if __name__ == "__main__":
    export_schema()

