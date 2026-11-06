"""Automated benchmark comparing Traditional Granular Editing vs HyperEdit Fast Production Mode."""

import json
from pathlib import Path
import shutil
import subprocess
import time

from hyperedit.adapters.hyperframes import HyperFramesAdapter
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.audio.mixer import AudioMixer
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.models.transitions import Transition, TransitionType
from hyperedit.media.prober import FFprobeProber
from hyperedit.production.engine import FastProductionEngine
from hyperedit.production.models import (
    AudioDesign,
    MotionGraphicOverlay,
    ProductionMode,
    ProductionPlan,
    SceneCut,
)
from hyperedit.production.profiler import get_peak_memory_mb
from hyperedit.rendering.engine import RenderEngine


def generate_benchmark_assets(work_dir: Path) -> dict[str, Path]:
    """Generate minimal broadcast-standard media for benchmark."""
    work_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg required for benchmark.")

    clip_a = work_dir / "shot_a.mp4"
    clip_b = work_dir / "shot_b.mp4"
    music = work_dir / "soundtrack.wav"
    dialogue = work_dir / "voice.wav"

    # Clip A: 2.0s 720p blue
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=2.0:r=30",
            "-f", "lavfi", "-i", "sine=f=440:d=2.0:r=48000",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(clip_a)
        ],
        check=True,
        capture_output=True,
    )

    # Clip B: 2.0s 720p red
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=red:s=1280x720:d=2.0:r=30",
            "-f", "lavfi", "-i", "sine=f=880:d=2.0:r=48000",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(clip_b)
        ],
        check=True,
        capture_output=True,
    )

    # Music: 4.0s soundtrack
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "sine=f=220:d=4.0:r=48000",
            str(music)
        ],
        check=True,
        capture_output=True,
    )

    # Dialogue: 2.0s speech trigger
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "sine=f=1200:d=2.0:r=48000",
            str(dialogue)
        ],
        check=True,
        capture_output=True,
    )

    return {"clip_a": clip_a, "clip_b": clip_b, "music": music, "dialogue": dialogue}


def run_traditional_flow(assets: dict[str, Path], output_dir: Path) -> dict:
    """Simulates traditional granular flow where AI Agent executes 9+ separate steps without caching."""
    output_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()
    cpu_start = time.process_time()

    prober = FFprobeProber()
    tracker = BeatTracker()
    hyperframes = HyperFramesAdapter()
    mixer = AudioMixer()
    renderer = RenderEngine()

    operations = 0
    t_analysis = 0.0
    t_render = 0.0

    # Step 1-4: Agent probes each asset in separate turns
    ta0 = time.perf_counter()
    p_a = prober.probe_file(assets["clip_a"])
    operations += 1
    p_b = prober.probe_file(assets["clip_b"])
    operations += 1
    prober.probe_file(assets["music"])
    operations += 1
    p_d = prober.probe_file(assets["dialogue"])
    operations += 1

    # Step 5: Agent runs audio beat analysis
    tracker.analyze_beats(assets["music"])
    operations += 1
    t_analysis += (time.perf_counter() - ta0)

    # Step 6: Agent generates and renders motion graphics overlay
    tr0 = time.perf_counter()
    comp_html = output_dir / "title.html"
    hyperframes.create_composition("title_comp", "cinematic_intro", {"title": "HERO INTRO"}, comp_html, duration_sec=2.0)
    operations += 1
    overlay_mov = output_dir / "overlay.mov"
    hyperframes.render_composition(comp_html, overlay_mov)
    operations += 1
    prober.probe_file(overlay_mov)
    operations += 1

    # Step 7: Agent applies sidechain ducking
    ducked_wav = output_dir / "ducked_music.wav"
    mixer.apply_sidechain_ducking(assets["music"], assets["dialogue"], ducked_wav, threshold_db=-20.0, mix_with_dialogue=False)
    operations += 1
    prober.probe_file(ducked_wav)
    operations += 1

    # Step 8: Agent manually constructs multi-track timeline JSON
    project = Project(
        metadata=ProjectMetadata(title="Traditional Project"),
        settings=ProjectSettings(width=1280, height=720, fps=30.0),
        timeline=Timeline(
            tracks=[
                Track(
                    track_id="V1",
                    name="Video",
                    kind=TrackKind.VIDEO,
                    clips=[
                        Clip(clip_id="c1", asset_id=p_a.asset_id, in_frame=0, out_frame=45, timeline_start_frame=0),
                        Clip(clip_id="c2", asset_id=p_b.asset_id, in_frame=0, out_frame=45, timeline_start_frame=45, transition_in=Transition(type=TransitionType.CROSSFADE, duration_frames=10)),
                    ],
                ),
                Track(
                    track_id="GRAPHIC",
                    name="Graphics",
                    kind=TrackKind.GRAPHIC,
                    clips=[
                        Clip(clip_id="mg1", asset_id="mg_overlay", in_frame=0, out_frame=60, timeline_start_frame=0),
                    ],
                ),
                Track(
                    track_id="A1",
                    name="Voice",
                    kind=TrackKind.AUDIO,
                    clips=[Clip(clip_id="v1", asset_id=p_d.asset_id, in_frame=0, out_frame=60, timeline_start_frame=0)],
                ),
                Track(
                    track_id="A2",
                    name="Music",
                    kind=TrackKind.AUDIO,
                    clips=[Clip(clip_id="m1", asset_id="ducked_music", in_frame=0, out_frame=90, timeline_start_frame=0)],
                ),
            ]
        ),
    )
    project.media_pool.add_asset(p_a)
    project.media_pool.add_asset(p_b)
    project.media_pool.add_asset(p_d)
    project.media_pool.add_asset(MediaAsset(asset_id="mg_overlay", file_path=str(overlay_mov), duration_seconds=2.0, has_video=True, has_alpha=True))
    project.media_pool.add_asset(MediaAsset(asset_id="ducked_music", file_path=str(ducked_wav), duration_seconds=3.0, has_audio=True))
    project.validate_integrity()
    operations += 1

    # Step 9: Agent renders master deliverable (without prior low-res preflight)
    master_file = output_dir / "traditional_master.mp4"
    preset = ExportPreset(name="web_720p", width=1280, height=720, fps=30.0, hwaccel=HardwareAccel.AUTO)
    renderer.render_project(project, preset, master_file)
    operations += 1
    t_render += (time.perf_counter() - tr0)

    total_wall = time.perf_counter() - t_start
    total_cpu = time.process_time() - cpu_start
    peak_mem = get_peak_memory_mb()

    return {
        "flow": "Traditional Granular",
        "model_turns_required": 9,
        "operations_total": operations,
        "operations_cached": 0,
        "re_renders_avoided": 0,
        "cache_hit_ratio": 0.0,
        "analysis_time_sec": round(t_analysis, 3),
        "render_time_sec": round(t_render, 3),
        "total_elapsed_sec": round(total_wall, 3),
        "cpu_time_sec": round(total_cpu, 3),
        "peak_memory_mb": round(peak_mem, 1),
        "remediation_attempts": 0,
    }


def run_fast_production_flow(assets: dict[str, Path], output_dir: Path, is_warm: bool = False) -> dict:
    """Executes HyperEdit Fast Production flow: 1 declarative plan, automatic caching & preflight."""
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_file = output_dir / ("plan_warm.json" if is_warm else "plan_cold.json")
    master_file = output_dir / ("master_warm.mp4" if is_warm else "master_cold.mp4")

    plan = ProductionPlan(
        title="Fast Production Campaign",
        mode=ProductionMode.FAST,
        preset="1080p",
        width=1280,
        height=720,
        fps=30.0,
        cuts=[
            SceneCut(clip_id="c1", source_asset=str(assets["clip_a"]), in_seconds=0.0, out_seconds=1.5),
            SceneCut(clip_id="c2", source_asset=str(assets["clip_b"]), in_seconds=0.0, out_seconds=1.5, transition="crossfade", transition_duration_sec=0.3),
        ],
        audio=AudioDesign(
            music_file=str(assets["music"]),
            dialogue_file=str(assets["dialogue"]),
            ducking=True,
            beat_sync=True,
        ),
        motion_graphics=[
            MotionGraphicOverlay(
                template="cinematic_intro",
                title="HERO INTRO",
                preset="cinematic_luxury",
                start_seconds=0.0,
                duration_seconds=2.0,
                sync_beats=True,
            )
        ],
        output_path=str(master_file),
        cache_dir=str(output_dir / ".cache"),
    )
    plan.save_to_file(plan_file)

    engine = FastProductionEngine()
    result = engine.run(plan, resume=True)

    return {
        "flow": "Fast Production (Warm Cache)" if is_warm else "Fast Production (Cold)",
        "model_turns_required": 1,
        "operations_total": result.metrics.operations_total,
        "operations_cached": result.metrics.operations_cached,
        "re_renders_avoided": result.metrics.re_renders_avoided,
        "cache_hit_ratio": result.metrics.cache_hit_ratio,
        "analysis_time_sec": result.metrics.analysis_seconds,
        "render_time_sec": result.metrics.render_seconds,
        "total_elapsed_sec": result.metrics.total_elapsed_seconds,
        "cpu_time_sec": result.metrics.cpu_seconds,
        "peak_memory_mb": result.metrics.peak_memory_mb,
        "remediation_attempts": result.metrics.remediation_attempts,
    }


def main():
    bench_dir = Path("benchmark_temp").resolve()
    shutil.rmtree(bench_dir, ignore_errors=True)
    bench_dir.mkdir(parents=True, exist_ok=True)

    print("Generating deterministic test media...")
    assets = generate_benchmark_assets(bench_dir / "assets")

    print("\n[1/3] Benchmarking Flow A: Traditional Granular Multi-Turn...")
    res_trad = run_traditional_flow(assets, bench_dir / "traditional")

    print("\n[2/3] Benchmarking Flow B: Fast Production Mode (Cold Build)...")
    res_fast_cold = run_fast_production_flow(assets, bench_dir / "fast_cold", is_warm=False)

    print("\n[3/3] Benchmarking Flow C: Fast Production Mode (Warm Cache & Re-run)...")
    res_fast_warm = run_fast_production_flow(assets, bench_dir / "fast_cold", is_warm=True)

    results = [res_trad, res_fast_cold, res_fast_warm]

    # Save benchmark telemetry to disk
    telemetry_file = bench_dir / "benchmark_report.json"
    telemetry_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Print markdown table
    print("\n" + "=" * 95)
    print("HYPEREDIT PRO — BENCHMARK RESULTS: TRADITIONAL VS FAST PRODUCTION MODE")
    print("=" * 95)
    print(f"{'Metric':<30} | {'Traditional Flow':<20} | {'Fast Mode (Cold)':<20} | {'Fast Mode (Warm)':<20}")
    print("-" * 95)
    print(f"{'Model Turns Required':<30} | {res_trad['model_turns_required']:<20} | {res_fast_cold['model_turns_required']:<20} | {res_fast_warm['model_turns_required']:<20}")
    print(f"{'Total Operations':<30} | {res_trad['operations_total']:<20} | {res_fast_cold['operations_total']:<20} | {res_fast_warm['operations_total']:<20}")
    print(f"{'Cached Operations':<30} | {res_trad['operations_cached']:<20} | {res_fast_cold['operations_cached']:<20} | {res_fast_warm['operations_cached']:<20}")
    print(f"{'Cache Hit Ratio':<30} | {res_trad['cache_hit_ratio']*100:.1f}%{'':<15} | {res_fast_cold['cache_hit_ratio']*100:.1f}%{'':<15} | {res_fast_warm['cache_hit_ratio']*100:.1f}%{'':<15}")
    print(f"{'Re-renders Avoided':<30} | {res_trad['re_renders_avoided']:<20} | {res_fast_cold['re_renders_avoided']:<20} | {res_fast_warm['re_renders_avoided']:<20}")
    print(f"{'Analysis Time (s)':<30} | {res_trad['analysis_time_sec']:<20} | {res_fast_cold['analysis_time_sec']:<20} | {res_fast_warm['analysis_time_sec']:<20}")
    print(f"{'Render Time (s)':<30} | {res_trad['render_time_sec']:<20} | {res_fast_cold['render_time_sec']:<20} | {res_fast_warm['render_time_sec']:<20}")
    print(f"{'Total Elapsed Time (s)':<30} | {res_trad['total_elapsed_sec']:<20} | {res_fast_cold['total_elapsed_sec']:<20} | {res_fast_warm['total_elapsed_sec']:<20}")
    print(f"{'CPU Time (s)':<30} | {res_trad['cpu_time_sec']:<20} | {res_fast_cold['cpu_time_sec']:<20} | {res_fast_warm['cpu_time_sec']:<20}")
    print(f"{'Peak RSS Memory (MB)':<30} | {res_trad['peak_memory_mb']:<20} | {res_fast_cold['peak_memory_mb']:<20} | {res_fast_warm['peak_memory_mb']:<20}")
    print(f"{'Recovery / Circuit Breaker':<30} | {'None':<20} | {'Max 2 Active':<20} | {'Max 2 Active':<20}")
    print("=" * 95)

    # Cleanup test media
    shutil.rmtree(bench_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
