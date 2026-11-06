# CLI Guide

## Commands

### `hyperedit doctor`
Audits system environment, verifies FFmpeg and FFprobe binaries, inspects available hardware acceleration encoders, and tests core video/audio filters.
- `--json`: Output report as JSON.
- `-v, --verbose`: Print detailed component properties.
- `--strict`: Return exit code 2 on warnings.

### `hyperedit version`
Displays HyperEdit Pro version and project schema specification version.
- `--json`: Output as JSON.

### `hyperedit new <project.json>`
Scaffolds a new project file.
- `--title <TEXT>`: Project title.
- `--preset [1080p|vertical_1080p|4k|square]`: Canvas aspect ratio and dimensions.
- `--fps <FLOAT>`: Framerate (default 30.0).
- `--force`: Overwrite existing file.

### `hyperedit validate <project.json>`
Validates project JSON against schema and integrity rules.
- `--json`: Output result as JSON.

### `hyperedit probe <media_file>`
Inspects a media file via `ffprobe` and extracts stream metadata.
- `--json`: Output as JSON.
- `--hash`: Compute SHA-256 asset checksum.

