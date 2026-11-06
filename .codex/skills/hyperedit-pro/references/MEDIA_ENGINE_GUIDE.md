# HyperEdit Pro Media Engine Technical Guide

This guide defines the engineering principles, standards, and handling strategies implemented by the **HyperEdit Pro Professional Media Engine**.

---

## 1. Frame Rate Mathematics & Timing Precision

Audiovisual drift occurs when fractional frame rates are approximated as floating-point seconds (e.g. treating 29.97 as 30 or 29.9700000). HyperEdit Pro handles all time calculations using exact rational fractions (`fractions.Fraction`):

| Nominal FPS | Exact Fraction ($\text{num}/\text{den}$) | Standard Usage |
| :--- | :--- | :--- |
| **23.976** | $24000 / 1001$ | Cinema, NTSC Film transfers, streaming drama |
| **24.0** | $24 / 1$ | DCI Theatrical standard |
| **25.0** | $25 / 1$ | PAL / European broadcast & web |
| **29.97** | $30000 / 1001$ | NTSC broadcast, American television |
| **30.0** | $30 / 1$ | Web video standard, computer graphics |
| **50.0** | $50 / 1$ | European high frame rate, sports |
| **59.94** | $60000 / 1001$ | High frame rate NTSC broadcast |
| **60.0** | $60 / 1$ | Gaming captures, high frame rate web |

### Constant Frame Rate (CFR) vs. Variable Frame Rate (VFR)
- Mobile devices (iPhone, Android) and screen recorders (OBS, Zoom) often record in **Variable Frame Rate (VFR)** to save bandwidth or accommodate frame drops.
- **VFR Detection**: HyperEdit Pro compares `r_frame_rate` (nominal stream rate) and `avg_frame_rate` (average rate computed from packet timestamps). If $|r - avg| > 0.05$, the stream is marked `is_vfr = True`.
- **Handling**: VFR files are flagged with warnings during validation. Generating a constant frame rate editing proxy (`hyperedit media proxy <file>`) ensures frame-accurate seeking and prevents timeline audio desynchronization.

---

## 2. Audio Channel Topologies

The Media Engine supports diverse audio channel mappings:

### Mono Audio (1 Channel)
- Probed as `channels=1`, `channel_layout="mono"`.
- When integrated into stereo master timelines, mono dialogue is centered ($L = R = \text{signal}$) or panned via track mixing faders.

### Stereo Audio (2 Channels)
- Probed as `channels=2`, `channel_layout="stereo"`.
- Standard delivery format for podcasts, music, and online video.

### 5.1 Surround Sound (6 Channels)
- Probed as `channels=6`, `channel_layout="5.1"` (`FL, FR, FC, LFE, BL, BR`).
- Can be downmixed to stereo using ITU-R BS.775 coefficient matrix:
  $$L = FL + 0.7071 \cdot FC + 0.7071 \cdot BL$$
  $$R = FR + 0.7071 \cdot FC + 0.7071 \cdot BR$$

### Silent Media (Videos without Audio)
- Many video assets (B-roll, stock footage, timelapse) have zero audio streams (`audio_streams = []`).
- **Engineering Guarantee**: The Media Engine detects `has_audio = False` and automatically adjusts pipeline operations. It never attempts to run audio filters (`showwavespic`, `volumedetect`, audio extraction) on silent assets, avoiding FFmpeg execution errors.

---

## 3. Spatial Orientation & Vertical Media

### Aspect Ratio Detection
- Landscape: $16:9$ ($1920 \times 1080$), $21:9$ ($2560 \times 1080$), $4K$ ($3840 \times 2160$).
- Portrait / Vertical: $9:16$ ($1080 \times 1920$), $4:5$ ($1080 \times 1350$).
- Square: $1:1$ ($1080 \times 1080$).

### Smartphone Metadata Rotation
Smartphone recordings often encode landscape video dimensions ($1920 \times 1080$) with a metadata rotation tag (`rotate: 90`, `rotate: 270`, or `displaymatrix` side data).
- The Media Engine inspects rotation metadata.
- If rotated $90^\circ$ or $270^\circ$, `is_vertical` is correctly set to `True`, and thumbnail/proxy generation filters automatically respect or apply rotation flags.

---

## 4. Multi-Resolution Timelines

Projects often mix $4K$ A-roll, $1080p$ B-roll, and $720p$ archive footage:
- The master canvas dimensions are set in `project.settings` (e.g. $1920 \times 1080$).
- When assets differ from canvas dimensions, the engine supports three fitting strategies:
  1. **Fit / Letterbox**: Scales video until the largest dimension matches canvas; pads remaining space with black borders.
  2. **Fill / Crop**: Scales video until the smallest dimension fills canvas; crops overflowing edges.
  3. **Custom Transform**: Keyframed scale, position, and anchor coordinates.

---

## 5. Performance with Multi-Gigabyte Media Files

To remain fast and memory-efficient with $50\text{ GB}+$ raw footage:
1. **Streaming Metadata Probing**: FFprobe reads container headers without decoding video frames or loading the file into system RAM.
2. **Chunk-Based Fast Fingerprinting**: Rather than hashing an entire 100 GB file, `MediaCacheManager` hashes the file size, modification timestamp (`st_mtime_ns`), and the first $64\text{ KB}$ + last $64\text{ KB}$ of data. This validates or invalidates cache entries in under $1\text{ ms}$.
3. **Editing Proxies**: Fast H.264 intra-friendly $720p$ or $540p$ proxies reduce decoding overhead by up to $80\%$, enabling responsive editing on lightweight hardware.

---

## 6. Cross-Platform Path Handling

To guarantee reliability across Windows, macOS, and Linux:
1. **Unicode Support**: Full support for accented characters (`á, é, í, ó, ú, ñ`), spaces, and non-Latin/emoji scripts (e.g. `video_verano_2026_🎬.mp4`).
2. **Windows Path Normalization**: Resolves paths to absolute canonical forms (`Path(p).resolve()`), handling Windows drive letters (`C:\`), forward/backward slashes, and extended-length path prefixes (`\\?\`).
3. **Atomic Cache Writing**: Cache records are written to a temporary file (`.tmp`) and replaced atomically to prevent corruption during unexpected shutdowns or multi-agent concurrent writes.

