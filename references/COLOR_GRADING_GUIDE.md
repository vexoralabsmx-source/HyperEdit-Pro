# HyperEdit Pro: Professional Color Correction & Grading Engine Guide

## 1. Executive Architecture & Mission

HyperEdit Pro integrates a non-destructive, broadcast-compliant color grading and color correction pipeline for autonomous AI agents. The engine combines digital signal analysis (histograms, IRE luma levels, dynamic range evaluation) with deterministic FFmpeg and OpenCV filters.

### Design Principles (Compliant with `AGENTS.md`):
- **Conservative & Reproducible**: Never apply heavy crushed looks automatically across all footage.
- **Reversible by Design**: All grades are parameterized via [`ColorGradeConfig`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/core/models/color.py) and can be toggled (`enabled: bool = False`) or faded with `preset_strength`.
- **Broadcast Legality & No Unnecessary Clipping**: Protects deep shadows and specular highlights, guarding against harsh digital clipping.
- **Strict Color Management**: Audits color primaries, transfer characteristics, and luminance ranges (SDR Rec.709 vs HDR10 PQ / HLG) prior to processing.

---

## 2. Core Color Correction Controls

### 2.1 Exposure, Contrast & Saturation
- **Exposure Bias (`exposure_ev: float`)**: Measured in photographic Exposure Value (EV) stops ($-3.0$ to $+3.0$ EV). Each $+1.0$ EV doubles linear luminance.
- **Contrast Multiplier (`contrast: float`)**: Linear contrast adjustment centered at mid-gray ($1.0$ = neutral).
- **Saturation (`saturation: float`)**: Chroma scale factor ($1.0$ = neutral, $0.0$ = pure monochrome, $>1.0$ = boosted chroma).
- **Vibrance (`vibrance: float`)**: Non-linear saturation boost that protects skin tones and saturated pixels from over-saturation.

### 2.2 Color Temperature & Tint
- **Temperature (`temperature: float`)**: Shifts white balance between cool blue ($-100$) and warm orange ($+100$).
- **Tint (`tint: float`)**: Shifts green ($-100$) to magenta ($+100$).
- *Mathematical Basis*: In shot matching, chromaticity coordinates are normalized independently of exposure ($r_n = R / \sum, b_n = B / \sum$) to isolate true chromatic casts.

### 2.3 Black Point & White Point
- **Black Point (`black_point: float`)**: Controls shadow pedestal and black crush ($-0.2$ to $+0.2$). Positive values lift blacks; negative values crush them.
- **White Point (`white_point: float`)**: Controls highlight ceiling and roll-off ($0.8$ to $1.2$). Prevents digital blowing of specular details.

### 2.4 Three-Way Color Wheels: Lift, Gamma, Gain
Adjusts shadows, midtones, and highlights independently:
- **Lift**: Shadow color balance ($rs, gs, bs$).
- **Gamma**: Midtone color balance ($rm, gm, bm$).
- **Gain**: Highlight color balance ($rh, gh, bh$).

### 2.5 ASC Color Decision List (ASC-CDL)
Standardized primary color grading transfer function:
$$\text{out} = \text{clamp}\left((\text{in} \times \text{slope} + \text{offset})^{\text{power}}, 0.0, 1.0\right)$$
Followed by standard Rec.709 saturation weighting:
$$\text{out}_{rgb} = \text{luma} + \text{saturation} \times (\text{out}_{rgb} - \text{luma})$$

---

## 3. Curated Look Presets

HyperEdit Pro provides 6 non-generic cinematographic looks that can be blended at any strength ($0.0 \dots 1.0$):

| Preset Name | Art Direction Character | Key Adjustments |
| :--- | :--- | :--- |
| `cinematic_neutral` | Subtle S-curve contrast, neutral skin tones, gentle highlight roll-off. | Contrast: $1.08$, Sat: $0.96$, Black: $+0.01$, White: $0.98$. |
| `warm_editorial` | Golden hour warmth, lifted matte shadows, rich skin tones. | Exposure: $+0.1$ EV, Temp: $+18.0$, Black: $+0.02$, Warm lift/gain. |
| `cool_scandi` | Crisp Scandinavian atmosphere, cyan shadow undertone, clean whites. | Contrast: $1.12$, Sat: $0.88$, Temp: $-16.0$, Tint: $-4.0$. |
| `film_stock_5207` | Kodak Vision3 250D motion picture film stock emulation. | ASC-CDL slope/offset, split-tone warm midtones and teal shadow undertone. |
| `monochrome_panchro` | Classic black-and-white panchromatic response with high contrast. | Saturation: $0.0$, Contrast: $1.28$, Custom 4-point S-curve. |
| `bleach_bypass` | High-contrast desaturated look inspired by silver retention processing. | Contrast: $1.40$, Saturation: $0.55$, Lift: $-0.03$, Gain: $+1.10$. |

---

## 4. 3D Look-Up Table (.cube) Engine

HyperEdit Pro includes a full parser, generator, and trilinear interpolator for `.cube` 3D LUT files in [`CubeLUT`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/color/cube_lut.py):
- Parses 3D tables of standard sizes ($17\times 17\times 17$, $33\times 33\times 33$, $65\times 65\times 65$).
- Applies vector trilinear interpolation across 8 cube vertices:
  $$\mathbf{C}(r, g, b) = \sum_{i,j,k \in \{0, 1\}} w_{ijk} \cdot \mathbf{V}_{ijk}$$
- Compiles into FFmpeg's `lut3d=file='...':interp=tetrahedral` for high-throughput video rendering.
- Can generate synthetic `.cube` files for offline or test pipelines.

---

## 5. Shot Matching & Tonal Consistency

When intercutting clips filmed in varying lighting conditions, [`ColorGradingEngine.match_shots()`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/color/engine.py) matches tonal characteristics:
1. **Luma Matching**: Computes exposure offset $\Delta \text{EV} = \log_2\left(\frac{\mu_{\text{ref\_luma}}}{\mu_{\text{tgt\_luma}}}\right)$.
2. **Contrast Alignment**: Computes contrast ratio $c_{\text{match}} = \frac{\sigma_{\text{ref\_luma}}}{\sigma_{\text{tgt\_luma}}}$.
3. **Chromatic Balance**: Evaluates normalized chromaticity deltas $(\Delta r_n, \Delta b_n)$ to compute temperature and tint compensation.
4. Generates a non-destructive `ColorGradeConfig` and computes residual error metrics.

---

## 6. Color Management: SDR vs HDR Audit

In [`ColorGradingEngine.audit_color_space()`](file:///c:/Users/migue/Desktop/hyperedit%20pro/src/hyperedit/color/engine.py):
- Probes `color_space`, `color_primaries`, `color_transfer`, and `color_range` using FFprobe.
- **SDR Rec.709 Baseline**: Standard 8-bit or 10-bit broadcast gamma ($2.4$), BT.709 primaries, limited range ($16\text{--}235$) or full range ($0\text{--}255$).
- **HDR Detection**: Flags transfer functions such as `smpte2084` (HDR10 PQ) or `arib-std-b67` (HLG). Warns when HDR footage requires tone mapping prior to SDR export to avoid washed-out highlights.

---

## 7. CLI Command Reference

### `hyperedit color presets`
List all built-in color presets with numerical parameters.
```bash
hyperedit color presets [--json]
```

### `hyperedit color grade`
Apply color grading parameters or preset looks to video.
```bash
hyperedit color grade footage.mp4 -o graded.mp4 --preset warm_editorial --strength 0.85
hyperedit color grade footage.mp4 -o graded.mp4 --exposure 0.5 --contrast 1.15 --temp 10.0
hyperedit color grade footage.mp4 -o graded.mp4 --lut creative.cube
```

### `hyperedit color analyze`
Extract histogram metrics, IRE levels, dynamic range, and clipping telemetry.
```bash
hyperedit color analyze footage.mp4 [--json] [--histogram-output histogram.png]
```

### `hyperedit color match`
Align target shot tonal consistency to a reference shot.
```bash
hyperedit color match reference_shot.mp4 target_shot.mp4 -o matched_target.mp4 [--json]
```

### `hyperedit color audit`
Audit color space, primaries, transfer function, and SDR/HDR legality.
```bash
hyperedit color audit footage.mp4 [--json]
```

