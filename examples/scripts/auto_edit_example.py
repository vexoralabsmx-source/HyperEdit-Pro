"""Complete programmatic example of HyperEdit Pro: building an automated video project."""

from pathlib import Path
from hyperedit.core.models.color import ColorGradeConfig
from hyperedit.core.models.export import ExportPreset, HardwareAccel
from hyperedit.core.models.media import MediaAsset
from hyperedit.core.models.project import Project, ProjectMetadata, ProjectSettings
from hyperedit.core.models.timeline import Clip, Timeline, Track, TrackKind
from hyperedit.core.models.transitions import Transition, TransitionType
from hyperedit.rendering.engine import RenderEngine


def create_sample_automated_project(output_json: Path) -> Project:
    """Demonstrates building a multi-track Non-Linear Edited project in pure Python."""
    project = Project(
        metadata=ProjectMetadata(
            title="Automated Editorial Project",
            description="Multi-track project with transitions, color grading, and audio bed",
            author="HyperEdit Pro Autonomous Agent",
        ),
        settings=ProjectSettings(
            width=1920,
            height=1080,
            fps=30.0,
            sample_rate=48000,
        ),
        timeline=Timeline(
            tracks=[
                Track(
                    track_id="V1",
                    name="Primary A-Roll",
                    kind=TrackKind.VIDEO,
                    clips=[
                        Clip(
                            clip_id="clip_intro",
                            asset_id="footage_host",
                            in_frame=0,
                            out_frame=90,  # 3.0 seconds
                            timeline_start_frame=0,
                            color_grade=ColorGradeConfig(
                                preset_name="warm_editorial",
                                preset_strength=0.9,
                            ),
                        ),
                        Clip(
                            clip_id="clip_scene2",
                            asset_id="footage_host",
                            in_frame=90,
                            out_frame=180,  # 3.0 seconds
                            timeline_start_frame=90,
                            transition_in=Transition(
                                type=TransitionType.CROSSFADE,
                                duration_frames=15,  # 0.5s dissolve
                            ),
                            color_grade=ColorGradeConfig(
                                preset_name="cinematic_neutral",
                                contrast=1.12,
                            ),
                        ),
                    ],
                ),
                Track(
                    track_id="A1",
                    name="Soundtrack Bed",
                    kind=TrackKind.AUDIO,
                    clips=[
                        Clip(
                            clip_id="audio_bgm",
                            asset_id="music_track",
                            in_frame=0,
                            out_frame=180,
                            timeline_start_frame=0,
                            volume_db=-14.0,  # Ducked volume
                        )
                    ],
                ),
            ]
        ),
    )

    # Register assets in media pool
    project.media_pool.add_asset(
        MediaAsset(
            asset_id="footage_host",
            file_path="assets/host_interview.mp4",
            duration_seconds=10.0,
            file_size_bytes=10485760,
            width=1920,
            height=1080,
            fps=30.0,
        )
    )
    project.media_pool.add_asset(
        MediaAsset(
            asset_id="music_track",
            file_path="assets/soundtrack.mp3",
            duration_seconds=180.0,
            file_size_bytes=5242880,
        )
    )

    project.validate_integrity()
    project.save_to_file(output_json)
    print(f"Saved project JSON to: {output_json}")
    return project


if __name__ == "__main__":
    demo_path = Path("sample_editorial_project.json")
    proj = create_sample_automated_project(demo_path)

    # To render the project:
    # engine = RenderEngine()
    # preset = ExportPreset(name="web_1080p", width=1920, height=1080, fps=30.0, hwaccel=HardwareAccel.AUTO)
    # engine.render_project(proj, preset, "master_output.mp4")

