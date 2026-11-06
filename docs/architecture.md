# Architecture Overview

HyperEdit Pro is built on three core foundations:

1. **Deterministic Frame Mathematics**:
   All positions on tracks are expressed in absolute integer frames. Frame rate is tracked as an exact rational fraction (e.g. $24000/1001$ for 23.976 fps).

2. **Decoupled Protocols**:
   Every subsystem (audio mixing, subtitles, motion, tracking, color grading, QA) implements a strict `typing.Protocol`. Implementations can be tested in isolation or substituted without modifying the core project engine.

3. **FFmpeg Complex Filtergraph Compiler**:
   Multi-track video and audio compositions compile down to single deterministic `-filter_complex` commands with stream-level PTS resets and hardware acceleration.

