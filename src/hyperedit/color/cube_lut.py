"""Adobe / DaVinci Resolve .cube 3D Look-Up Table (LUT) parser, generator and interpolator."""

from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np

from hyperedit.core.exceptions import AdapterError, MediaNotFoundError


class CubeLUT:
    """Reader, writer and high-precision 3D trilinear interpolator for .cube files."""

    def __init__(self, size: int, table: np.ndarray, title: str = "HyperEditLUT") -> None:
        self.size = size
        self.table = table  # Shape: (size, size, size, 3) in RGB order
        self.title = title

    @classmethod
    def from_file(cls, cube_path: Path | str) -> "CubeLUT":
        """Parse an industry-standard .cube 3D LUT file."""
        p = Path(cube_path).resolve()
        if not p.is_file():
            raise MediaNotFoundError(f"3D LUT file not found: {p}")

        title = p.stem
        size = 0
        data_rows: List[List[float]] = []

        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("TITLE"):
                    parts = line.split(maxsplit=1)
                    if len(parts) > 1:
                        title = parts[1].replace('"', '').strip()
                elif line.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[1])
                elif line.startswith("DOMAIN_MIN") or line.startswith("DOMAIN_MAX"):
                    continue
                else:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                            data_rows.append([r, g, b])
                        except ValueError:
                            continue

        if size == 0:
            raise AdapterError(f"Invalid .cube file, missing LUT_3D_SIZE in: {p.name}")
        expected_points = size ** 3
        if len(data_rows) < expected_points:
            raise AdapterError(f"Malformed .cube file: expected {expected_points} entries, got {len(data_rows)}")

        # .cube specification stores red moving fastest, then green, then blue
        # R index increases first, then G, then B
        raw_arr = np.array(data_rows[:expected_points], dtype=np.float32)
        table = raw_arr.reshape((size, size, size, 3), order="F")

        return cls(size=size, table=table, title=title)

    def save(self, output_path: Path | str) -> Path:
        """Write LUT table to disk as a standardized .cube file."""
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)

        with open(p, "w", encoding="utf-8") as f:
            f.write(f'TITLE "{self.title}"\n')
            f.write(f"LUT_3D_SIZE {self.size}\n")
            f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
            f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
            f.write("\n")

            # Output in column-major order matching R fastest, G second, B third
            for b in range(self.size):
                for g in range(self.size):
                    for r in range(self.size):
                        rgb = self.table[r, g, b]
                        f.write(f"{rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}\n")

        return p

    def apply_to_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Apply 3D LUT to a BGR image frame using vector trilinear interpolation."""
        h, w = frame_bgr.shape[:2]
        # Normalize to float [0.0, 1.0] in RGB order
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        scale = self.size - 1
        pos = np.clip(rgb * scale, 0.0, scale)

        # Coordinate floor and ceiling
        r0 = np.floor(pos[:, :, 0]).astype(np.int32)
        r1 = np.clip(r0 + 1, 0, scale)
        g0 = np.floor(pos[:, :, 1]).astype(np.int32)
        g1 = np.clip(g0 + 1, 0, scale)
        b0 = np.floor(pos[:, :, 2]).astype(np.int32)
        b1 = np.clip(b0 + 1, 0, scale)

        # Fractional weights
        fr = np.expand_dims(pos[:, :, 0] - r0, axis=2)
        fg = np.expand_dims(pos[:, :, 1] - g0, axis=2)
        fb = np.expand_dims(pos[:, :, 2] - b0, axis=2)

        # 8 cube corners
        c000 = self.table[r0, g0, b0]
        c100 = self.table[r1, g0, b0]
        c010 = self.table[r0, g1, b0]
        c110 = self.table[r1, g1, b0]
        c001 = self.table[r0, g0, b1]
        c101 = self.table[r1, g0, b1]
        c011 = self.table[r0, g1, b1]
        c111 = self.table[r1, g1, b1]

        # Trilinear interpolation
        c00 = c000 * (1.0 - fr) + c100 * fr
        c10 = c010 * (1.0 - fr) + c110 * fr
        c01 = c001 * (1.0 - fr) + c101 * fr
        c11 = c011 * (1.0 - fr) + c111 * fr

        c0 = c00 * (1.0 - fg) + c10 * fg
        c1 = c01 * (1.0 - fg) + c11 * fg

        out_rgb = c0 * (1.0 - fb) + c1 * fb
        out_rgb = np.clip(out_rgb * 255.0, 0, 255).astype(np.uint8)

        # Return in BGR
        return cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

    @classmethod
    def generate_creative_lut(cls, size: int = 17, style: str = "warm_golden") -> "CubeLUT":
        """Generate a procedural 3D LUT table for creative styling."""
        grid = np.linspace(0.0, 1.0, size, dtype=np.float32)
        R, G, B = np.meshgrid(grid, grid, grid, indexing="ij")
        table = np.zeros((size, size, size, 3), dtype=np.float32)

        if style == "warm_golden":
            # Golden highlight warmth, slight contrast lift
            table[:, :, :, 0] = np.clip(R ** 0.95 * 1.04 + 0.01, 0.0, 1.0)
            table[:, :, :, 1] = np.clip(G ** 0.98 * 1.02, 0.0, 1.0)
            table[:, :, :, 2] = np.clip(B ** 1.05 * 0.94 - 0.005, 0.0, 1.0)
        elif style == "teal_orange":
            # Teal shadows (blue/green boost), orange highlights (red/green boost)
            luma = 0.2126 * R + 0.7152 * G + 0.0722 * B
            table[:, :, :, 0] = np.clip(np.where(luma > 0.5, R * 1.08, R * 0.90), 0.0, 1.0)
            table[:, :, :, 1] = np.clip(G * 1.01, 0.0, 1.0)
            table[:, :, :, 2] = np.clip(np.where(luma < 0.5, B * 1.12 + 0.02, B * 0.88), 0.0, 1.0)
        else:
            # Identity LUT
            table[:, :, :, 0] = R
            table[:, :, :, 1] = G
            table[:, :, :, 2] = B

        return cls(size=size, table=table, title=f"HyperEdit_{style}")

