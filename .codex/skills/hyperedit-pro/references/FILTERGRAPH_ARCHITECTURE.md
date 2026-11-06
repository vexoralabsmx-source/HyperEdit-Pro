# HyperEdit Pro Filtergraph Compilation Architecture

## 1. Deterministic Graph Generation

HyperEdit Pro translates a multi-track project into a single, deterministic FFmpeg `-filter_complex` execution graph. The graph guarantees zero audio/video drift by enforcing:
1. Universal framerate synchronization using `fps=fps=<project_fps>` and `settb=AVTB`.
2. Exact presentation timestamp resets (`setpts=PTS-STARTPTS`).
3. Audio sample rate resampling to master standard (`aresample=48000:async=1`).

---

## 2. Visual Track Compositing Pipeline

For $N$ video tracks ordered by index $0 \dots N-1$:
1. Base canvas generator initializes `color=c=black:s=WxH:r=fps`.
2. Each clip applies its local transform:
   ```
   [input] trim=start_frame:end_frame, setpts=PTS-STARTPTS,
           scale=w:h, pad=canvas_w:canvas_h:x:y, setsar=1 [v_clip]
   ```
3. Adjacent clips on the same track with transitions compile to `xfade`:
   ```
   [v_clip1][v_clip2] xfade=transition=fade:duration=0.5:offset=10.0 [v_track1]
   ```
4. Higher indexed tracks composite over lower tracks via `overlay`:
   ```
   [v_track0][v_track1] overlay=x=0:y=0:enable='between(t, start, end)' [v_master]
   ```

---

## 3. Audio Mixing & Sidechain Ducking Pipeline

Audio streams compile through a multi-stage routing matrix:
1. **Source Trimming**: `atrim=start:end, asetpts=PTS-STARTPTS, volume=volume_db dB`.
2. **Sidechain Ducking**:
   When background music (BGM) has a `DuckingConfig` triggered by Dialogue:
   ```
   [bgm][dialogue] sidechaincompress=threshold=0.05:ratio=4:attack=80:release=400 [bgm_ducked]
   ```
3. **Master Bus Summing**:
   All active audio tracks are mixed via `amix=inputs=M:normalize=0`.
4. **Loudness Normalization (EBU R128)**:
   ```
   [a_summed] loudnorm=I=-23:LRA=7:TP=-1.0:dual_mono=false [a_master]
   ```

