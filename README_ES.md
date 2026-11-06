# HyperEdit Pro 🎬 (Guía en Español)

> **Motor Autónomo de Posproducción y Edición No Lineal (NLE) para Agentes de IA, Complementario a HyperFrames.**

[![CI](https://github.com/vexoralabsmx-source/HyperEdit-Pro/actions/workflows/ci.yml/badge.svg)](https://github.com/vexoralabsmx-source/HyperEdit-Pro/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-vexoralabsmx--source%2FHyperEdit--Pro-181717?logo=github)](https://github.com/vexoralabsmx-source/HyperEdit-Pro)
[![Agent Skills](https://img.shields.io/badge/Est%C3%A1ndar-Agent%20Skills%20v1.0-8A2BE2)](SKILL.md)

[English](README.md) | [Español](README_ES.md)

---

## 1. ¿Qué es HyperEdit Pro?

**HyperEdit Pro** es un motor de posproducción audiovisual no destructivo de código abierto, diseñado específicamente para agentes autónomos de IA (**OpenAI Codex**, **Claude Code**, **Cursor**, **Gemini CLI** / **Antigravity**).

A diferencia de los asistentes basados exclusivamente en prompts que simulan capacidades de video mediante texto, HyperEdit Pro provee herramientas ejecutables reales. Controla directamente **FFmpeg**, **FFprobe**, **OpenCV** y encoders de aceleración por hardware a través de un esquema JSON de línea de tiempo versionado (`schema_version: 2.0.0`).

### Principios Fundamentales de Diseño:
- **Cero Herramientas Alucinadas**: Todos los cortes, mezclas de audio, subtítulos cinéticos, correcciones de color y renders ejecutan código real verificado mediante telemetría de señal.
- **Matemática Discreta de Fotogramas**: Los límites temporales se definen como enteros exactos (`in_frame`, `out_frame`, `timeline_start_frame`), evitando el desfase acumulativo de coma flotante.
- **Inmutabilidad del Material Original**: El metraje y los audios fuente nunca se modifican en disco; todas las operaciones son no destructivas.
- **Operación Local Primero**: Funciona íntegramente en CPU y GPU local sin depender obligatoriamente de APIs o servicios en la nube.

---

## 2. Matriz de Capacidades Operativas

| Subsistema | Capacidades Reales | Estado |
| :--- | :--- | :--- |
| **Media Engine** | Inspección multi-stream con FFprobe (CFR/VFR 23.976 a 60 fps), miniaturas, hojas de contacto 3x3, gráficos de forma de onda PNG, proxies 720p y caché atómico. | ✅ Operativo |
| **Línea de Tiempo y Edición** | Línea de tiempo multipista (`V1`–`V2`, `A1`–`A3`, `GRAPHIC`), cortes exactos, inserción ripple/overwrite, trim, split, ripple delete, transiciones (`xfade`) e historial reversible de deshacer/rehacer. | ✅ Operativo |
| **Ingeniería de Audio y Beat Sync** | Detección de BPM y transientes en tiempo real desde la señal acústica, ajuste automático de cortes a los beats musicales, mezcla multipista, sidechain ducking y normalización de sonoridad EBU R128 / YouTube. | ✅ Operativo |
| **Subtítulos y Tipografía Cinética** | Conversión bidireccional SRT/VTT/ASS, compilación tipográfica ASS v4.00+, resaltado sincrónico por palabra (`karaoke_highlight`, `pop_scale`, `word_reveal`), transcripción local con `faster-whisper` y validación de zonas seguras (16:9 y 9:16). | ✅ Operativo |
| **Motion Graphics (HyperFrames)** | Integración con el contrato de HyperFrames (`data-composition-id`, `window.__timelines`), 6 presets de dirección de arte, interpolación Bézier cúbica y oscilador armónico (`spring`), cámara Ken Burns y exportación con canal alfa ProRes 4444. | ✅ Operativo |
| **VFX, Tracking e Integración 3D** | Seguimiento por correlación cruzada y flujo óptico Lucas-Kanade, estabilización de video 2D, máscaras animadas con feathering, chroma keying con canal alfa real, efectos cinemáticos (grano, shake, bloom) y adaptador headless para Blender 3D. | ✅ Operativo |
| **Corrección y Grading de Color** | Exposición en EV stops, contraste, saturación, vibrance, atenuación de negros y blancos, balance de blancos normalizado (temperatura/tinte), ruedas de 3 vías (Lift/Gamma/Gain), ASC-CDL, parser/interpolador de LUTs 3D `.cube` y emparejamiento automático de tomas (*shot matching*). | ✅ Operativo |

---

## 3. Relación entre HyperEdit Pro y HyperFrames

HyperEdit Pro es el complemento de posproducción y montaje cinematográfico para **HyperFrames**:

```
┌──────────────────────────────────────────────────────────┐
│                   FLUJO CREATIVO                         │
├─────────────────────────────┬────────────────────────────┤
│         HYPERFRAMES         │       HYPEREDIT PRO        │
│    (Motor Motion Graphics)  │   (Montaje y Posproducción)│
├─────────────────────────────┼────────────────────────────┤
│ • Animación HTML/CSS/GSAP   │ • Edición multi-cámara     │
│ • Captura de UI y Títulos   │ • Recortes, cortes ripple  │
│ • Lower-Thirds Animados     │ • Ducking de audio y R128  │
│ • Gráficos Cinéticos 2D/3D  │ • Chroma keying y VFX      │
│ • Renderiza .mov con alfa   │ • Color grading y LUTs 3D  │
└──────────────┬──────────────┴─────────────┬──────────────┘
               │                            │
               └────────► [COMPOSITOR] ◄────┘
               Overlay ProRes 4444 montado
               en la pista 'GRAPHIC' del timeline
```

---

## 4. Instalación

### Requisitos del Sistema
- **Python**: $\ge 3.11$
- **FFmpeg y FFprobe**: $\ge 5.0$ instalados y accesibles en el `PATH` del sistema.
- **Git**

### Instalación Rápida
```bash
# Clonar el repositorio oficial
git clone https://github.com/vexoralabsmx-source/HyperEdit-Pro.git
cd HyperEdit-Pro

# Instalar en modo editable
pip install -e .

# O instalar con soporte de visión artificial (OpenCV para tracking y chroma key)
pip install -e ".[vision]"

# Instalar con todas las dependencias opcionales (transcripción ASR, detección de escenas, visión)
pip install -e ".[all]"
```

---

## 5. Configuración para Agentes de IA (Codex, Claude, Cursor, Gemini)

HyperEdit Pro cumple con la especificación estándar **Agent Skills** (`SKILL.md`). Puede instalarse en el entorno de cualquier agente con un solo comando:

```bash
# Instalar en el workspace actual para todos los agentes detectados
python scripts/install_skill.py --agent all --workspace .

# O instalar globalmente en el directorio de usuario (~/)
python scripts/install_skill.py --agent all --global
```

- **OpenAI Codex**: Descubre `<workspace>/.codex/skills/hyperedit-pro/SKILL.md` o `~/.codex/skills/`.
- **Claude Code**: Descubre `<workspace>/.claude/skills/hyperedit-pro/SKILL.md` o `~/.claude/skills/`.
- **Cursor**: Descubre `<workspace>/.cursor/skills/hyperedit-pro/SKILL.md`.
- **Gemini CLI / Antigravity**: Descubre `~/.gemini/antigravity/skills/hyperedit-pro/` o `~/.agents/skills/`.

Consulte la guía completa en [docs/AGENT_INSTALLATION.md](docs/AGENT_INSTALLATION.md).

---

## 6. Diagnóstico del Entorno

Antes de comenzar a editar, verifique que los binarios y encoders de aceleración por hardware estén activos:

```bash
hyperedit doctor --verbose
```

Para agentes de IA que requieran salida en JSON estructurado:
```bash
hyperedit doctor --json
```

---

## 7. Guía de Inicio Rápido (CLI)

### 1. Inicializar un Proyecto
```bash
hyperedit project create mi_proyecto.json --preset 1080p --fps 30.0
```

### 2. Inspeccionar Material Audiovisual
```bash
hyperedit media probe tomas/entrevista.mp4 --json
```

### 3. Sincronizar Cortes a los Beats Musicales
```bash
hyperedit audio snap mi_proyecto.json musica/soundtrack.mp3 --track V1 --max-shift 8 --mode ripple
```

### 4. Generar Subtítulos con Resaltado Dinámico
```bash
hyperedit captions transcribe audio/voz.wav -o subs.srt --model base
hyperedit captions kinetic subs.srt -o kinetic.ass --mode karaoke_highlight --preset tiktok_reels_neon
hyperedit captions burn tomas/video.mp4 kinetic.ass -o video_subtitulado.mp4
```

### 5. Corrección de Color y Emparejamiento Tonal (Shot Matching)
```bash
# Emparejar la consistencia tonal entre toma secundaria y toma principal
hyperedit color match toma_principal.mp4 toma_secundaria.mp4 -o toma_secundaria_corregida.mp4

# Aplicar look de película 35mm (Kodak 5207) al 85% de intensidad
hyperedit color grade toma_secundaria_corregida.mp4 -o master_color.mp4 --preset film_stock_5207 --strength 0.85
```

### 6. Renderizar el Master Final
```bash
hyperedit render mi_proyecto.json -o master_final.mp4 --preset web_1080p --hwaccel auto
```

---

## 8. Límites y Fronteras del Motor

- **Aceleración por Hardware**: Detección automática de NVENC, VideoToolbox y QSV; si los controladores no están disponibles en tiempo de ejecución, el motor recurre limpiamente a CPU (`libx264`).
- **Rotoscopía Inteligente**: Modelos neurales pesados (como SAM) requieren pesos externos; la rotoscopía nativa opera con GrabCut asistido por caja delimitadora.
- **Renderizado 3D**: Requiere tener instalado el ejecutable `blender` en el sistema; HyperEdit Pro ejecuta y orquesta renders headless, sin recrear un motor 3D dentro de Python.

---

## 9. Documentación y Referencias Técnicas

- [Manual de Operaciones para Agentes de IA](AGENTS.md)
- [Especificación Agent Skills](SKILL.md)
- [Manual de Referencia de la CLI](references/CLI_REFERENCE.md)
- [Guía de Corrección de Color y Tono](references/COLOR_GRADING_GUIDE.md)
- [Guía de VFX, Tracking y 3D](references/VFX_AND_TRACKING_GUIDE.md)
- [Guía de Motion Graphics y HyperFrames](references/MOTION_GRAPHICS_GUIDE.md)
- [Guía de Subtítulos y Tipografía Cinética](references/CAPTIONS_AND_TYPOGRAPHY_GUIDE.md)
- [Guía de Ingeniería de Audio y Sincronización](references/AUDIO_ENGINE_GUIDE.md)
- [Especificación del Formato de Proyecto](references/PROJECT_FORMAT.md)
- [Arquitectura del Compilador de Filtergraph](references/FILTERGRAPH_ARCHITECTURE.md)
- [Hoja de Ruta del Proyecto](ROADMAP.md)

---

## 10. Licencia

HyperEdit Pro se publica bajo la **Licencia MIT** — consulte el archivo [LICENSE](LICENSE) para más detalles. Propuesta para aprobación comunitaria.

