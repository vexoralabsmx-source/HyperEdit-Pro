"""CLI command group for creating and validating declarative production plans."""

import json
import click

from hyperedit.core.exceptions import HyperEditError
from hyperedit.production.models import (
    AudioDesign,
    CaptionConfig,
    MotionGraphicOverlay,
    ProductionMode,
    ProductionPlan,
    SceneCut,
    VFXConfig,
)


@click.group(name="plan")
def plan_group() -> None:
    """Manage declarative post-production plans for Fast Production Mode."""
    pass


@plan_group.command(name="init")
@click.option("-o", "--output", "output_file", type=click.Path(dir_okay=False), default="production_plan.json", help="Destination path for plan JSON.")
@click.option(
    "--preset",
    type=click.Choice(["fast_montage", "podcast_reel", "cinematic_promo"], case_sensitive=False),
    default="fast_montage",
    help="Starter production template.",
)
@click.option("--fps", type=float, default=30.0, help="Timeline base frame rate.")
def init_plan(output_file: str, preset: str, fps: float) -> None:
    """Initialize a starter declarative production plan."""
    if preset == "podcast_reel":
        plan = ProductionPlan(
            title="Podcast Social Reel",
            mode=ProductionMode.FAST,
            preset="vertical_1080p",
            fps=fps,
            cuts=[
                SceneCut(clip_id="host_hook", source_asset="assets/podcast_host.mp4", in_seconds=0.0, out_seconds=5.0),
                SceneCut(clip_id="guest_reaction", source_asset="assets/podcast_guest.mp4", in_seconds=5.0, out_seconds=10.0, transition="crossfade"),
            ],
            audio=AudioDesign(
                dialogue_file="assets/podcast_voice.wav",
                music_file="assets/music_bed.mp3",
                ducking=True,
                ducking_threshold_db=-22.0,
                ducking_attenuation_db=-16.0,
            ),
            motion_graphics=[
                MotionGraphicOverlay(
                    template="cinematic_intro",
                    title="THE UNTOLD STORY",
                    subtitle="Episode 42",
                    preset="bold_editorial",
                    start_seconds=0.0,
                    duration_seconds=3.0,
                )
            ],
            captions=CaptionConfig(burn_in=True, style_preset="tiktok_reels_neon", kinetic_mode="karaoke_highlight"),
            output_path="output/podcast_reel.mp4",
        )
    elif preset == "cinematic_promo":
        plan = ProductionPlan(
            title="Cinematic Commercial Promo",
            mode=ProductionMode.CINEMATIC,
            preset="1080p",
            fps=fps,
            cuts=[
                SceneCut(clip_id="scene_hero", source_asset="assets/hero_shot.mp4", in_seconds=0.0, out_seconds=4.0, color_preset="warm_editorial"),
                SceneCut(clip_id="scene_product", source_asset="assets/product_macro.mp4", in_seconds=0.0, out_seconds=4.0, transition="dip_black", color_preset="cinematic_neutral"),
            ],
            audio=AudioDesign(
                music_file="assets/cinematic_orchestral.mp3",
                beat_sync=True,
                target_lufs=-14.0,
            ),
            motion_graphics=[
                MotionGraphicOverlay(
                    template="cinematic_intro",
                    title="AURA LUXURY",
                    preset="cinematic_luxury",
                    start_seconds=0.0,
                    duration_seconds=3.5,
                    sync_beats=True,
                )
            ],
            vfx=VFXConfig(film_grain=0.15),
            output_path="output/cinematic_master.mp4",
        )
    else:  # fast_montage
        plan = ProductionPlan(
            title="Fast Dynamic Montage",
            mode=ProductionMode.FAST,
            preset="1080p",
            fps=fps,
            cuts=[
                SceneCut(clip_id="shot_1", source_asset="assets/shot_1.mp4", in_seconds=0.0, out_seconds=3.0),
                SceneCut(clip_id="shot_2", source_asset="assets/shot_2.mp4", in_seconds=0.0, out_seconds=3.0, transition="crossfade"),
            ],
            audio=AudioDesign(
                music_file="assets/upbeat_soundtrack.mp3",
                beat_sync=True,
            ),
            output_path="output/fast_montage.mp4",
        )

    out_p = plan.save_to_file(output_file)
    click.echo(f"Initialized declarative plan ({preset}) at: {out_p}")


@plan_group.command(name="validate")
@click.argument("plan_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "json_output", is_flag=True, help="Output machine-readable JSON status.")
def validate_plan(plan_file: str, json_output: bool) -> None:
    """Validate structure and syntax of a declarative production plan."""
    try:
        plan = ProductionPlan.load_from_file(plan_file)
        w, h = plan.get_dimensions()
        report = {
            "valid": True,
            "title": plan.title,
            "mode": plan.mode.value,
            "dimensions": f"{w}x{h}",
            "fps": plan.fps,
            "cuts_count": len(plan.cuts),
            "motion_graphics_count": len(plan.motion_graphics),
            "output_path": plan.output_path,
        }
        if json_output:
            click.echo(json.dumps(report, indent=2))
        else:
            click.echo(f"[OK] Production Plan is valid: {plan.title} ({plan.mode.value} mode, {w}x{h} @ {plan.fps} fps, {len(plan.cuts)} cuts)")
    except HyperEditError as e:
        if json_output:
            click.echo(json.dumps(e.to_dict(), indent=2))
        else:
            click.echo(f"[ERROR] Plan validation failed: {e.message}", err=True)
        raise click.exceptions.Exit(1)
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"valid": False, "error": str(e)}, indent=2))
        else:
            click.echo(f"[ERROR] Plan parsing error: {e}", err=True)
        raise click.exceptions.Exit(1)

