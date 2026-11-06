# Intelligent Audio Engineering & Beat Sync Guide

**HyperEdit Pro** features a professional acoustic signal analysis, beat synchronization, multi-bus audio mixing, sidechain ducking, and EBU R128 loudness engine.

All signal analyses and DSP operations run directly through FFmpeg and native Python math without third-party heavy dependencies like librosa or PyTorch.

---

## 1. Acoustic Signal Beat Tracking & Onsets

### 1.1 Pure Signal Processing Pipeline
Unlike tools that simulate BPM or read ID3 tags, `BeatTracker` decodes raw 16-bit mono PCM samples at 22050 Hz via FFmpeg stdout (`-f s16le -`):

1. **Short-Time RMS Energy Envelope**:
   $$\text{RMS}_w = \sqrt{\frac{1}{N} \sum_{i=0}^{N-1} s_i^2}$$
   Computed over 10ms hops ($N = 220$ samples).

2. **Half-Wave Rectified Spectral Flux (Novelty Curve)**:
   $$\mathcal{N}[k] = \max(0, \text{RMS}[k] - \text{RMS}[k-1])$$
   Captures transient attack energy rises while discarding decay slopes.

3. **Onset Detection**:
   Local peaks in $\mathcal{N}[k]$ that exceed dynamic threshold $\theta = 1.5 \times \text{mean}(\mathcal{N})$ with a 50ms minimum refractory window.

4. **Autocorrelation Tempo Estimation**:
   $$\mathcal{R}(\tau) = \sum_{j} \mathcal{N}[j] \cdot \mathcal{N}[j - \tau]$$
   Evaluated across lags corresponding to 45 BPM ($\tau \approx 1.33\text{s}$) to 220 BPM ($\tau \approx 0.27\text{s}$).

5. **First Downbeat Phase Alignment ($\phi$)**:
   Selects $\phi \in [0, T_{\text{beat}})$ maximizing grid alignment with detected transient energy peaks.

### 1.2 CLI Usage: Beat Analysis
```bash
# Analyze beats and print human-readable summary
hyperedit audio beats soundtrack.mp3

# Provide approximate tempo hint (e.g. 128 BPM house music)
hyperedit audio beats soundtrack.mp3 --bpm-hint 128.0

# Output structured JSON telemetry for automated agent pipelines
hyperedit audio beats soundtrack.mp3 --json
```

Output example:
```json
{
  "bpm": 120.0,
  "confidence": 0.88,
  "beat_interval_sec": 0.5,
  "beat_timestamps": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
  "onset_timestamps": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
  "time_signature": "4/4",
  "manual_bpm_override": null
}
```

---

## 2. Beat Synchronization & Timeline Snapping

### 2.1 Timeline Beat Markers
Visual markers can be automatically placed on the project timeline at each detected beat:
```bash
hyperedit audio markers project.json soundtrack.mp3 --color "#FF00AA"
```

### 2.2 Snapping Video Cuts to Beats
`BeatSynchronizer.snap_cuts_to_beats` automatically shifts edit cuts on any track (e.g. `V1`) to the closest musical beat within a frame tolerance threshold.

Two edit modes are supported:
- **`ripple` (Default)**: Extends/trims the tail of the preceding clip to hit the beat frame, then shifts all subsequent downstream clips forward or backward.
- **`roll`**: Adjusts the tail of the preceding clip and the head of the succeeding clip concurrently, keeping total track duration and downstream timing completely unchanged.

```bash
# Snap cuts on track V1 within +/- 8 frames tolerance
hyperedit audio snap project.json soundtrack.mp3 --track V1 --max-shift 8 --mode ripple

# Output detailed alignment telemetry report
hyperedit audio snap project.json soundtrack.mp3 --track V1 --json
```

Telemetry Report:
```json
{
  "track_id": "V1",
  "total_cuts_evaluated": 4,
  "cuts_snapped": 4,
  "max_shift_allowed_frames": 8,
  "mean_shift_ms": 66.67,
  "max_shift_ms": 100.0,
  "details": [
    {
      "clip_id": "c1",
      "original_frame": 17,
      "snapped_frame": 15,
      "shift_frames": -2,
      "shift_ms": -66.67,
      "beat_time_sec": 0.5
    }
  ]
}
```

---

## 3. Sidechain Ducking

`AudioMixer.apply_sidechain_ducking` routes background music through FFmpeg's `sidechaincompress` filter with a dialogue track acting as the control sidechain:

- When speech is detected above `threshold_db` (default -20 dBFS), music is automatically attenuated by `ratio` (default 4.0:1 to 6.0:1).
- `attack_ms` (default 20ms) smoothly dips the music without clicks.
- `release_ms` (default 250ms) recovers the music bed after the voice finishes speaking.
- Silence padding (`apad`) guarantees background music is never cut short when dialogue pauses.

### CLI Usage: Sidechain Ducking
```bash
# Output combined mix of ducked music + dialogue
hyperedit audio duck bg_music.wav dialogue.wav -o ducked_mix.wav --threshold -20 --ratio 5.0 --attack 20 --release 250 --mix

# Output ducked music bed only
hyperedit audio duck bg_music.wav dialogue.wav -o ducked_music_only.wav --music-only
```

---

## 4. Platform Loudness Compliance (EBU R128 & ITU-R BS.1770)

### 4.1 Standard Loudness Targets
| Platform | Standard | Target Integrated (LUFS) | Max True Peak (dBFS) | Target LRA (LU) |
|---|---|---|---|---|
| **YouTube** | Web Stream | **-14.0 LUFS** | **-1.0 dBFS** | 11.0 LU |
| **Spotify** | Audio Stream | **-14.0 LUFS** | **-1.0 dBFS** | 11.0 LU |
| **Apple Podcasts** | Podcast Standard | **-16.0 LUFS** | **-1.0 dBFS** | 9.0 LU |
| **EBU R128** | European Broadcast | **-23.0 LUFS** | **-1.0 dBFS** | 7.0 LU |
| **ATSC A/85** | US Television | **-24.0 LUFS** | **-1.0 dBFS** | 7.0 LU |

### 4.2 Measuring Loudness
Uses FFmpeg's `ebur128` filter to inspect audio compliance:
```bash
hyperedit audio loudness master.wav --profile youtube
```

Output:
```text
--- HyperEdit Pro: Loudness Telemetry (EBU R128) ---
  File:               master.wav
  Profile Target:     youtube (-14.0 LUFS)
  Integrated Loudness:-13.95 LUFS
  True Peak:          -2.10 dBFS
  Loudness Range:     6.40 LU
  Target Deviation:   +0.05 LU
  Status:             COMPLIANT
```

### 4.3 Normalizing Loudness
Applies FFmpeg's `loudnorm` filter to achieve exact platform standards:
```bash
# Normalize master to YouTube standard (-14 LUFS) at broadcast 48 kHz
hyperedit audio normalize raw_export.wav youtube_master.wav --profile youtube --sample-rate 48000

# Normalize to European Broadcast EBU R128 standard (-23 LUFS)
hyperedit audio normalize raw_export.wav ebu_master.wav --profile ebu_r128
```

---

## 5. Multi-Bus Timeline Audio Mixdown

Mixes all project audio tracks (`A1`, `A2`, `A3`, etc.), applies individual clip trims, delays, track faders, sidechain ducking, and master platform loudness normalization into a single WAV or MP3 stem:

```bash
hyperedit audio mix project.json -o master_soundtrack.wav --profile youtube --sample-rate 48000
```

