"""Fast Production Engine: declarative post-production orchestrator for AI agents."""

from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional

from hyperedit.adapters.hyperframes import HyperFramesAdapter
from hyperedit.audio.beat_sync import BeatSynchronizer
from hyperedit.audio.beat_tracker import BeatTracker
from hyperedit.audio.mixer import AudioMixer
from hyperedit.audio.models import BeatInfo
from hyperedit.core.exceptions import (
    MediaNotFoundError,
    ProductionPlanError,
    RenderExecutionError,
    TimelineIntegrityError,
)
from hyperedit.core.models.color import ColorGradeConfig
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.models.transitions import Transition, TransitionType
from hyperedit.media.cache import MediaCacheManager
from hyperedit.media.prober import FFprobeProber
from hyperedit.production.cache import ProductionCache
from hyperedit.production.checkpoint import ProductionCheckpointManager
from hyperedit.production.circuit_breaker import RemediationCircuitBreaker
from hyperedit.production.models import (
    ProductionPlan,
    ProductionResult,
    ProductionStage,
    SceneCut,
)
from hyperedit.production.preview import FastPreviewGenerator
from hyperedit.production.profiler import ProductionProfiler
from hyperedit.rendering.engine import RenderEngine


class FastProductionEngine:
    """Orchestrates end-to-end audiovisual video production from a single declarative plan."""

    def __init__(
        self,
        ffmpeg_bin: Optional[str] = None,
        ffprobe_bin: Optional[str] = None,
    ) -> None:
        self.ffmpeg_bin = ffmpeg_bin or shutil.which("ffmpeg")
        self.ffprobe_bin = ffprobe_bin or shutil.which("ffprobe")
        self.prober = FFprobeProber(ffprobe_bin=self.ffprobe_bin)
        self.media_cache = MediaCacheManager()
        self.render_engine = RenderEngine(ffmpeg_bin=self.ffmpeg_bin)
        self.hyperframes = HyperFramesAdapter(ffprobe_bin=self.ffprobe_bin)
        self.preview_generator = FastPreviewGenerator(ffmpeg_bin=self.ffmpeg_bin)

    def run(self, plan: ProductionPlan, resume: bool = True) -> ProductionResult:
        """Execute complete automated production lifecycle from a single declarative plan."""
        profiler = ProductionProfiler()
        profiler.start()

        plan_hash = plan.compute_plan_hash()
        cache = ProductionCache(plan.cache_dir)
        checkpoint = ProductionCheckpointManager(plan_hash, plan.cache_dir)
        circuit_breaker = RemediationCircuitBreaker(max_retries=2)

        output_path = Path(plan.output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        preview_target = (
            Path(plan.preview_path).resolve()
            if plan.preview_path
            else cache.preview_dir / f"preview_{plan_hash}.mp4"
        )

        # -------------------------------------------------------------
        # PHASE 1: ASSET PROBING & FINGERPRINTING
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        all_referenced_files: List[Path] = []
        for a in plan.assets:
            all_referenced_files.append(Path(a).resolve())
        for c in plan.cuts:
            all_referenced_files.append(Path(c.source_asset).resolve())
        if plan.audio.music_file:
            all_referenced_files.append(Path(plan.audio.music_file).resolve())
        if plan.audio.dialogue_file:
            all_referenced_files.append(Path(plan.audio.dialogue_file).resolve())

        # Deduplicate paths
        unique_paths = list(dict.fromkeys(all_referenced_files))
        probed_assets: Dict[str, MediaAsset] = {}

        for p in unique_paths:
            if not p.is_file():
                raise MediaNotFoundError(f"Source asset not found: {p}")

            cached_asset = self.media_cache.get(p)
            if cached_asset and resume:
                profiler.record_operation(is_cached=True, was_re_render_avoided=True)
                probed_assets[p.name] = cached_asset
                probed_assets[str(p)] = cached_asset
            else:
                asset = self.prober.probe_file(p)
                self.media_cache.set(p, asset)
                profiler.record_operation(is_cached=False)
                probed_assets[p.name] = asset
                probed_assets[str(p)] = asset

        profiler.add_analysis_time(time.perf_counter() - t0)
        checkpoint.record_stage(ProductionStage.ASSETS_PROBED)

        # -------------------------------------------------------------
        # PHASE 2: AUDIO ANALYSIS & BEAT/DUCKING CACHE
        # -------------------------------------------------------------
        t1 = time.perf_counter()
        beat_info: Optional[BeatInfo] = None
        if (plan.audio.beat_sync or any(m.sync_beats for m in plan.motion_graphics)) and plan.audio.music_file:
            music_p = Path(plan.audio.music_file).resolve()
            cached_beats = cache.get_audio_beats(music_p)
            if cached_beats and resume:
                profiler.record_operation(is_cached=True, was_re_render_avoided=True)
                beat_info = cached_beats
            else:
                tracker = BeatTracker(ffmpeg_bin=self.ffmpeg_bin)
                detected = tracker.analyze_beats(music_p)
                cache.store_audio_beats(music_p, detected)
                profiler.record_operation(is_cached=False)
                beat_info = detected

        # Sidechain ducking stem if dialogue and music are both present
        ducked_music_path: Optional[Path] = None
        if plan.audio.ducking and plan.audio.music_file and plan.audio.dialogue_file:
            m_p = Path(plan.audio.music_file).resolve()
            d_p = Path(plan.audio.dialogue_file).resolve()
            cached_duck = cache.get_ducked_audio(
                m_p, d_p, plan.audio.ducking_threshold_db, plan.audio.ducking_attenuation_db
            )
            if cached_duck and resume:
                profiler.record_operation(is_cached=True, was_re_render_avoided=True)
                ducked_music_path = cached_duck
            else:
                mixer = AudioMixer(ffmpeg_bin=self.ffmpeg_bin)
                temp_duck = cache.stems_dir / f"temp_duck_{plan_hash}.wav"
                mixer.apply_sidechain_ducking(
                    music_file=m_p,
                    dialogue_file=d_p,
                    output_file=temp_duck,
                    threshold_db=plan.audio.ducking_threshold_db,
                    makeup_db=0.0,
                    mix_with_dialogue=False,
                )
                ducked_music_path = cache.store_ducked_audio(
                    m_p, d_p, plan.audio.ducking_threshold_db, plan.audio.ducking_attenuation_db, temp_duck
                )
                profiler.record_operation(is_cached=False)

        profiler.add_analysis_time(time.perf_counter() - t1)
        checkpoint.record_stage(ProductionStage.AUDIO_ANALYZED)

        # -------------------------------------------------------------
        # PHASE 3: MOTION GRAPHICS (HYPERFRAMES) COMPOSITION & CACHE
        # -------------------------------------------------------------
        t2 = time.perf_counter()
        width, height = plan.get_dimensions()
        fps = plan.fps
        rendered_motion_clips: List[Dict[str, Any]] = []

        for m_idx, mg in enumerate(plan.motion_graphics):
            cached_mov = cache.get_motion_overlay(
                template=mg.template,
                title=mg.title,
                subtitle=mg.subtitle,
                preset=mg.preset,
                width=width,
                height=height,
                fps=fps,
                duration=mg.duration_seconds,
            )
            if cached_mov and resume:
                profiler.record_operation(is_cached=True, was_re_render_avoided=True)
                motion_path = cached_mov
            else:
                comp_html = cache.motion_dir / f"comp_{mg.template}_{m_idx}_{plan_hash}.html"
                self.hyperframes.create_composition(
                    composition_id=f"mg_{m_idx}",
                    template_type=mg.template,
                    params={"title": mg.title, "subtitle": mg.subtitle or ""},
                    output_file=comp_html,
                    preset_name=mg.preset,
                    width=width,
                    height=height,
                    duration_sec=mg.duration_seconds,
                )
                if mg.sync_beats and beat_info:
                    self.hyperframes.sync_with_audio_beats(comp_html, beat_info)

                temp_render = cache.motion_dir / f"render_{mg.template}_{m_idx}_{plan_hash}.mov"
                self.hyperframes.render_composition(
                    composition_file=comp_html,
                    output_path=temp_render,
                    format="mov",
                    fps=fps,
                    transparent=True,
                )
                motion_path = cache.store_motion_overlay_path(
                    template=mg.template,
                    title=mg.title,
                    subtitle=mg.subtitle,
                    preset=mg.preset,
                    width=width,
                    height=height,
                    fps=fps,
                    duration=mg.duration_seconds,
                    source_file=temp_render,
                )
                profiler.record_operation(is_cached=False)

            # Probe the rendered overlay to register in media pool
            mg_asset = self.prober.probe_file(motion_path)
            rendered_motion_clips.append({
                "clip_id": f"clip_mg_{m_idx}",
                "asset_id": f"asset_mg_{m_idx}",
                "asset": mg_asset,
                "start_seconds": mg.start_seconds,
                "duration_seconds": mg.duration_seconds,
                "track": mg.track,
            })

        profiler.add_analysis_time(time.perf_counter() - t2)
        checkpoint.record_stage(ProductionStage.MOTION_COMPOSED)

        # -------------------------------------------------------------
        # PHASE 4: DETERMINISTIC TIMELINE ASSEMBLY
        # -------------------------------------------------------------
        t3 = time.perf_counter()
        project = Project(
            metadata=ProjectMetadata(title=plan.title, description=f"Automated {plan.mode} post-production"),
            settings=ProjectSettings(
                width=width,
                height=height,
                fps=fps,
                sample_rate=48000,
            ),
            timeline=Timeline(tracks=[]),
        )

        # Register probed assets in project media pool
        for key, asset in probed_assets.items():
            if asset.asset_id not in project.media_pool.assets:
                project.media_pool.add_asset(asset)

        for mg_item in rendered_motion_clips:
            project.media_pool.add_asset(
                MediaAsset(
                    asset_id=mg_item["asset_id"],
                    file_path=str(mg_item["asset"].file_path),
                    duration_seconds=mg_item["duration_seconds"],
                    width=width,
                    height=height,
                    fps=fps,
                    has_video=True,
                    has_alpha=True,
                )
            )

        # Track V1: Primary Cuts
        v1_clips: List[Clip] = []
        current_v1_frame = 0

        # Auto-generate cuts if not explicitly specified but assets provided
        cuts_to_process = list(plan.cuts)
        if not cuts_to_process and plan.assets:
            for idx, a_path in enumerate(plan.assets):
                cuts_to_process.append(
                    SceneCut(
                        clip_id=f"auto_cut_{idx}",
                        source_asset=a_path,
                        in_seconds=0.0,
                        out_seconds=3.0,
                    )
                )

        for cut in cuts_to_process:
            src_p = Path(cut.source_asset).resolve()
            asset_ref = probed_assets.get(src_p.name) or probed_assets.get(str(src_p))
            if not asset_ref:
                raise ProductionPlanError(f"Cut refers to unprobed asset: {cut.source_asset}")

            asset_id = asset_ref.asset_id
            asset_dur = asset_ref.duration_seconds or 10.0

            in_sec = cut.in_seconds if cut.in_seconds is not None else 0.0
            out_sec = cut.out_seconds if cut.out_seconds is not None else min(asset_dur, in_sec + 3.0)
            in_frame = int(round(in_sec * fps))
            out_frame = int(round(out_sec * fps))
            dur_frames = max(1, out_frame - in_frame)

            trans_in = None
            if cut.transition:
                trans_type = (
                    TransitionType.DIP_TO_BLACK
                    if "black" in cut.transition.lower()
                    else TransitionType.CROSSFADE
                )
                trans_in = Transition(
                    type=trans_type,
                    duration_frames=int(round(cut.transition_duration_sec * fps)),
                )

            cg_config = None
            if cut.color_preset:
                cg_config = ColorGradeConfig(preset_name=cut.color_preset, enabled=True)

            clip_obj = Clip(
                clip_id=cut.clip_id,
                asset_id=asset_id,
                in_frame=in_frame,
                out_frame=out_frame,
                timeline_start_frame=current_v1_frame,
                speed=cut.speed,
                reverse=cut.reverse,
                transition_in=trans_in,
                color_grade=cg_config,
            )
            v1_clips.append(clip_obj)
            current_v1_frame += dur_frames

        project.timeline.add_track(
            Track(track_id="V1", name="Primary Video", kind=TrackKind.VIDEO, clips=v1_clips)
        )

        # Snap cuts to beats if requested
        if plan.audio.beat_sync and beat_info and len(v1_clips) >= 2:
            sync = BeatSynchronizer(default_fps=fps)
            sync.snap_cuts_to_beats(
                timeline=project.timeline,
                track_id="V1",
                beats=beat_info,
                max_shift_frames=plan.audio.beat_sync_max_shift_frames,
                fps=fps,
            )

        # Track GRAPHIC: Motion Overlays
        if rendered_motion_clips:
            graphic_clips: List[Clip] = []
            for mg_item in rendered_motion_clips:
                mg_start_f = int(round(mg_item["start_seconds"] * fps))
                mg_dur_f = int(round(mg_item["duration_seconds"] * fps))
                graphic_clips.append(
                    Clip(
                        clip_id=mg_item["clip_id"],
                        asset_id=mg_item["asset_id"],
                        in_frame=0,
                        out_frame=mg_dur_f,
                        timeline_start_frame=mg_start_f,
                    )
                )
            project.timeline.add_track(
                Track(track_id="GRAPHIC", name="Motion Graphics", kind=TrackKind.GRAPHIC, clips=graphic_clips)
            )

        # Track A1: Dialogue (if present)
        if plan.audio.dialogue_file:
            d_p = Path(plan.audio.dialogue_file).resolve()
            d_asset = probed_assets.get(d_p.name) or probed_assets.get(str(d_p))
            if d_asset and d_asset.has_audio:
                dur_f = int(round((d_asset.duration_seconds or 10.0) * fps))
                a1_clip = Clip(
                    clip_id="clip_dialogue",
                    asset_id=d_asset.asset_id,
                    in_frame=0,
                    out_frame=dur_f,
                    timeline_start_frame=0,
                )
                project.timeline.add_track(
                    Track(track_id="A1", name="Dialogue", kind=TrackKind.AUDIO, clips=[a1_clip])
                )

        # Track A2: Background Music (ducked or original)
        music_final_path = ducked_music_path if ducked_music_path else plan.audio.music_file
        if music_final_path:
            m_p = Path(music_final_path).resolve()
            m_asset = (
                self.prober.probe_file(m_p)
                if ducked_music_path
                else (probed_assets.get(m_p.name) or probed_assets.get(str(m_p)))
            )
            if m_asset:
                if m_asset.asset_id not in project.media_pool.assets:
                    project.media_pool.add_asset(m_asset)

                # Duration matches timeline length
                tot_dur_f = max(current_v1_frame, 30)
                a2_clip = Clip(
                    clip_id="clip_bgm",
                    asset_id=m_asset.asset_id,
                    in_frame=0,
                    out_frame=tot_dur_f,
                    timeline_start_frame=0,
                    volume_db=-14.0 if not ducked_music_path and plan.audio.ducking else 0.0,
                )
                project.timeline.add_track(
                    Track(track_id="A2", name="Soundtrack", kind=TrackKind.AUDIO, clips=[a2_clip])
                )

        # Validate project integrity
        try:
            project.validate_integrity()
        except TimelineIntegrityError as e:
            strategy = circuit_breaker.record_attempt("timeline_integrity", e)
            if strategy == "ripple_shift_colliding_clips":
                for track in project.timeline.tracks:
                    track.close_gaps_ripple()
                project.validate_integrity()

        profiler.add_analysis_time(time.perf_counter() - t3)
        checkpoint.record_stage(ProductionStage.TIMELINE_ASSEMBLED)

        # -------------------------------------------------------------
        # PHASE 5: FAST PREFLIGHT PREVIEW & CIRCUIT-BREAKER VALIDATION
        # -------------------------------------------------------------
        preview_elapsed = 0.0
        try:
            _, preview_elapsed = self.preview_generator.generate_preview(
                project=project,
                mode=plan.mode,
                output_file=preview_target,
            )
            profiler.add_render_time(preview_elapsed)
            profiler.record_operation(is_cached=False)
            checkpoint.record_stage(
                ProductionStage.PREVIEW_VERIFIED,
                intermediate_files={"preview_path": str(preview_target)},
            )
        except RenderExecutionError as e:
            remediation = circuit_breaker.record_attempt("preview_preflight", e)
            if remediation == "force_even_dimensions":
                project.settings.width = (project.settings.width // 2) * 2
                project.settings.height = (project.settings.height // 2) * 2
                _, preview_elapsed = self.preview_generator.generate_preview(
                    project=project, mode=plan.mode, output_file=preview_target
                )
            elif remediation == "fallback_software_x264":
                _, preview_elapsed = self.preview_generator.generate_preview(
                    project=project, mode=plan.mode, output_file=preview_target
                )
            else:
                raise

        # -------------------------------------------------------------
        # PHASE 6: MASTER RENDER
        # -------------------------------------------------------------
        t4 = time.perf_counter()
        master_preset = ExportPreset(
            name=f"{plan.preset}_master",
            width=width,
            height=height,
            fps=fps,
            video_bitrate_kbps=8000 if width >= 1920 else 4000,
            audio_bitrate_kbps=192,
            audio_sample_rate=48000,
            hwaccel=HardwareAccel.AUTO,
        )

        try:
            self.render_engine.render_project(project, master_preset, output_path)
            profiler.add_render_time(time.perf_counter() - t4)
            profiler.record_operation(is_cached=False)
            checkpoint.record_stage(
                ProductionStage.MASTER_RENDERED,
                intermediate_files={"master_path": str(output_path)},
            )
        except RenderExecutionError as e:
            strategy = circuit_breaker.record_attempt("master_render", e)
            if strategy == "fallback_software_x264":
                master_preset.hwaccel = HardwareAccel.NONE
                self.render_engine.render_project(project, master_preset, output_path)
                profiler.add_render_time(time.perf_counter() - t4)
            else:
                raise

        # -------------------------------------------------------------
        # PHASE 7: TELEMETRY & COMPACT AGENT SUMMARY
        # -------------------------------------------------------------
        profiler.remediation_attempts = circuit_breaker.total_remediations
        metrics = profiler.finish()
        summary = ProductionProfiler.format_compact_summary(
            metrics=metrics,
            mode=plan.mode.value,
            output_file=str(output_path),
            preview_file=str(preview_target),
            remediations=circuit_breaker.applied_remediations,
        )

        checkpoint.record_stage(ProductionStage.COMPLETED)

        return ProductionResult(
            success=True,
            mode=plan.mode,
            output_file=str(output_path),
            preview_file=str(preview_target),
            metrics=metrics,
            compact_summary=summary,
            details={
                "plan_hash": plan_hash,
                "duration_seconds": project.duration_seconds,
                "tracks_count": len(project.timeline.tracks),
                "remediations": circuit_breaker.applied_remediations,
            },
        )

