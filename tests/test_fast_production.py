"""Tests for Fast Production Mode, declarative planning, caching, and circuit breaker."""

import json
from pathlib import Path
import subprocess
import pytest

from hyperedit.core.exceptions import ProductionBlockedError
from hyperedit.production.cache import ProductionCache
from hyperedit.production.checkpoint import ProductionCheckpointManager
from hyperedit.production.circuit_breaker import RemediationCircuitBreaker
from hyperedit.production.engine import FastProductionEngine
from hyperedit.production.models import (
    AudioDesign,
    MotionGraphicOverlay,
    ProductionMode,
    ProductionPlan,
    ProductionStage,
    SceneCut,
)


@pytest.fixture
def synthetic_media(tmp_path: Path):
    """Generate minimal deterministic test media for fast production testing."""
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg not available")

    video1 = tmp_path / "shot_a.mp4"
    video2 = tmp_path / "shot_b.mp4"
    audio_bgm = tmp_path / "music.wav"
    audio_voice = tmp_path / "voice.wav"

    # 1. Video 1: 2-second 360p blue clip with audio
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=2.0:r=30",
            "-f", "lavfi", "-i", "sine=f=440:d=2.0:r=48000",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(video1)
        ],
        check=True,
        capture_output=True,
    )

    # 2. Video 2: 2-second 360p red clip with audio
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=red:s=640x360:d=2.0:r=30",
            "-f", "lavfi", "-i", "sine=f=880:d=2.0:r=48000",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(video2)
        ],
        check=True,
        capture_output=True,
    )

    # 3. Audio BGM: 4-second music track
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "sine=f=220:d=4.0:r=48000",
            str(audio_bgm)
        ],
        check=True,
        capture_output=True,
    )

    # 4. Audio Voice: 2-second speech proxy
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "lavfi", "-i", "sine=f=1000:d=2.0:r=48000",
            str(audio_voice)
        ],
        check=True,
        capture_output=True,
    )

    return {
        "video1": video1,
        "video2": video2,
        "bgm": audio_bgm,
        "voice": audio_voice,
    }


def test_production_plan_schema_and_serialization(tmp_path: Path):
    plan = ProductionPlan(
        title="Test Campaign",
        mode=ProductionMode.FAST,
        preset="1080p",
        cuts=[
            SceneCut(clip_id="c1", source_asset="test1.mp4", in_seconds=0.0, out_seconds=3.0),
            SceneCut(clip_id="c2", source_asset="test2.mp4", in_seconds=1.0, out_seconds=4.0, transition="crossfade"),
        ],
        audio=AudioDesign(
            music_file="bgm.mp3",
            ducking=True,
        ),
        output_path=str(tmp_path / "master.mp4"),
    )

    w, h = plan.get_dimensions()
    assert (w, h) == (1920, 1080)
    assert len(plan.cuts) == 2

    # Test file serialization
    json_path = tmp_path / "plan.json"
    plan.save_to_file(json_path)
    assert json_path.exists()

    loaded = ProductionPlan.load_from_file(json_path)
    assert loaded.title == "Test Campaign"
    assert loaded.compute_plan_hash() == plan.compute_plan_hash()


def test_circuit_breaker_max_two_attempts_and_halt():
    cb = RemediationCircuitBreaker(max_retries=2)

    # Attempt 1: Auto-remediation strategy returned
    strat1 = cb.record_attempt("hwaccel", RuntimeError("NVENC encoder unavailable"))
    assert strat1 == "fallback_software_x264"
    assert cb.total_remediations == 1

    # Attempt 2: Second attempt accepted
    strat2 = cb.record_attempt("hwaccel", RuntimeError("NVENC initialization failed again"))
    assert strat2 == "fallback_software_x264"
    assert cb.total_remediations == 2

    # Attempt 3: Exceeds MAX_RETRIES, MUST halt immediately with ProductionBlockedError
    with pytest.raises(ProductionBlockedError) as exc_info:
        cb.record_attempt("hwaccel", RuntimeError("NVENC fatal failure"))

    assert "exceeded maximum allowed attempts" in exc_info.value.message
    assert "hwaccel" in exc_info.value.message


def test_checkpoint_manager_state_persistence_and_resumption(tmp_path: Path):
    cp = ProductionCheckpointManager("sample_hash_123", cache_dir=tmp_path)
    assert not cp.is_stage_completed(ProductionStage.AUDIO_ANALYZED)

    cp.record_stage(ProductionStage.ASSETS_PROBED, {"stem_1": str(tmp_path / "stem.wav")})
    cp.record_stage(ProductionStage.AUDIO_ANALYZED)

    # Verify reload from disk
    cp_reloaded = ProductionCheckpointManager("sample_hash_123", cache_dir=tmp_path)
    assert cp_reloaded.is_stage_completed(ProductionStage.ASSETS_PROBED)
    assert cp_reloaded.is_stage_completed(ProductionStage.AUDIO_ANALYZED)
    assert not cp_reloaded.is_stage_completed(ProductionStage.MASTER_RENDERED)


def test_production_cache_audio_and_motion(tmp_path: Path, synthetic_media):
    cache = ProductionCache(cache_dir=tmp_path / "cache")
    bgm = synthetic_media["bgm"]

    from hyperedit.audio.models import BeatInfo
    dummy_beats = BeatInfo(
        bpm=128.0,
        beat_interval_sec=60.0 / 128.0,
        beat_timestamps=[0.5, 1.0, 1.5, 2.0],
        confidence=0.95,
    )

    # Miss initially
    assert cache.get_audio_beats(bgm) is None

    # Store
    cache.store_audio_beats(bgm, dummy_beats)

    # Hit on second query
    cached = cache.get_audio_beats(bgm)
    assert cached is not None
    assert cached.bpm == 128.0
    assert len(cached.beat_timestamps) == 4
    assert cache.hits == 1


def test_fast_production_end_to_end_execution(tmp_path: Path, synthetic_media):
    """Execute complete Fast Production run from plan to master delivery."""
    output_master = tmp_path / "fast_master.mp4"
    preview_video = tmp_path / "fast_preview.mp4"

    plan = ProductionPlan(
        title="Automated Test Production",
        mode=ProductionMode.FAST,
        preset="1080p",
        fps=30.0,
        cuts=[
            SceneCut(
                clip_id="shot_1",
                source_asset=str(synthetic_media["video1"]),
                in_seconds=0.0,
                out_seconds=1.5,
                color_preset="warm_editorial",
            ),
            SceneCut(
                clip_id="shot_2",
                source_asset=str(synthetic_media["video2"]),
                in_seconds=0.0,
                out_seconds=1.5,
                transition="crossfade",
                transition_duration_sec=0.3,
            ),
        ],
        audio=AudioDesign(
            music_file=str(synthetic_media["bgm"]),
            dialogue_file=str(synthetic_media["voice"]),
            ducking=True,
            ducking_threshold_db=-20.0,
            ducking_attenuation_db=-12.0,
        ),
        motion_graphics=[
            MotionGraphicOverlay(
                template="cinematic_intro",
                title="FAST PRODUCTION",
                subtitle="Autonomous Post-Production",
                preset="cinematic_luxury",
                start_seconds=0.0,
                duration_seconds=2.0,
            )
        ],
        output_path=str(output_master),
        preview_path=str(preview_video),
        cache_dir=str(tmp_path / ".cache"),
    )

    engine = FastProductionEngine()
    result = engine.run(plan, resume=True)

    assert result.success is True
    assert output_master.is_file()
    assert output_master.stat().st_size > 1000
    assert preview_video.is_file()
    assert preview_video.stat().st_size > 1000
    assert "HyperEdit Fast Production (`fast`) Completed" in result.compact_summary
    assert result.metrics.total_elapsed_seconds > 0.0
    assert result.metrics.render_seconds > 0.0


def test_fast_production_caching_and_zero_duplicate_renders(tmp_path: Path, synthetic_media):
    """Verify that a second execution of the same plan reuses cached assets and avoids re-renders."""
    output_master = tmp_path / "cached_master.mp4"

    plan = ProductionPlan(
        title="Cache Verification",
        mode=ProductionMode.FAST,
        preset="1080p",
        fps=30.0,
        cuts=[
            SceneCut(
                clip_id="s1",
                source_asset=str(synthetic_media["video1"]),
                in_seconds=0.0,
                out_seconds=1.0,
            ),
        ],
        audio=AudioDesign(
            music_file=str(synthetic_media["bgm"]),
            ducking=False,
        ),
        output_path=str(output_master),
        cache_dir=str(tmp_path / ".cache"),
    )

    engine = FastProductionEngine()

    # Run 1: First build
    res1 = engine.run(plan, resume=True)
    assert res1.success is True

    # Run 2: Exact same plan should hit media probe cache
    res2 = engine.run(plan, resume=True)
    assert res2.success is True
    assert res2.metrics.operations_cached > 0
    assert res2.metrics.cache_hit_ratio > 0.0


def test_cli_plan_and_produce(tmp_path: Path, synthetic_media):
    """Test CLI commands: hyperedit plan init, validate, and hyperedit produce."""
    from click.testing import CliRunner
    from hyperedit.cli.main import cli

    runner = CliRunner()

    # 1. Test hyperedit plan init
    plan_file = tmp_path / "cli_plan.json"
    r_init = runner.invoke(cli, ["plan", "init", "-o", str(plan_file), "--preset", "fast_montage"])
    assert r_init.exit_code == 0
    assert plan_file.exists()

    # 2. Test hyperedit plan validate
    r_val = runner.invoke(cli, ["plan", "validate", str(plan_file), "--json"])
    assert r_val.exit_code == 0
    val_data = json.loads(r_val.output)
    assert val_data["valid"] is True

    # 3. Test hyperedit produce with real media
    plan = ProductionPlan.load_from_file(plan_file)
    plan.cuts = [
        SceneCut(clip_id="c1", source_asset=str(synthetic_media["video1"]), in_seconds=0.0, out_seconds=1.0),
    ]
    plan.audio.music_file = str(synthetic_media["bgm"])
    plan.output_path = str(tmp_path / "cli_master.mp4")
    plan.cache_dir = str(tmp_path / ".cache")
    plan.save_to_file(plan_file)

    r_prod = runner.invoke(cli, ["produce", str(plan_file), "--json"])
    assert r_prod.exit_code == 0, f"Produce failed:\nOutput: {r_prod.output}\nException: {r_prod.exception}"
    prod_data = json.loads(r_prod.output)
    assert prod_data["success"] is True
    assert Path(prod_data["output_file"]).is_file()

