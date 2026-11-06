"""Tests for Pydantic core data models, serialization, and integrity validation."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from hyperedit.core.exceptions import TimelineIntegrityError
from hyperedit.core.models import (
    Clip,
    Project,
)


def test_clip_duration_calculation():
    clip = Clip(
        clip_id="c1",
        asset_id="source1",
        in_frame=10,
        out_frame=100,
        timeline_start_frame=50,
        speed=1.0,
    )
    assert clip.source_duration_frames == 90
    assert clip.timeline_duration_frames == 90
    assert clip.timeline_end_frame == 140

    # Test 2x speed
    clip_2x = Clip(
        clip_id="c2",
        asset_id="source1",
        in_frame=0,
        out_frame=100,
        timeline_start_frame=0,
        speed=2.0,
    )
    assert clip_2x.timeline_duration_frames == 50
    assert clip_2x.timeline_end_frame == 50


def test_clip_invalid_in_out():
    with pytest.raises(ValidationError):
        # out_frame <= in_frame must fail validation
        Clip(
            clip_id="c_err",
            asset_id="src",
            in_frame=100,
            out_frame=50,
        )


def test_project_integrity_missing_asset(minimal_project):
    # Add clip with non-existent asset
    track = minimal_project.timeline.tracks[0]
    track.clips.append(
        Clip(
            clip_id="ghost_clip",
            asset_id="non_existent_asset_id",
            in_frame=0,
            out_frame=60,
            timeline_start_frame=200,
        )
    )
    with pytest.raises(TimelineIntegrityError) as exc_info:
        minimal_project.validate_integrity()
    assert "references unknown asset_id" in str(exc_info.value)


def test_project_integrity_collision_without_transition(minimal_project):
    track = minimal_project.timeline.tracks[0]
    # First clip ends at frame 150
    # Add colliding clip starting at frame 100 on the same track without transition
    track.clips.append(
        Clip(
            clip_id="colliding_clip",
            asset_id="test_vid",
            in_frame=0,
            out_frame=100,
            timeline_start_frame=100,
        )
    )
    with pytest.raises(TimelineIntegrityError) as exc_info:
        minimal_project.validate_integrity()
    assert "collide on track" in str(exc_info.value)


def test_project_serialization_roundtrip(minimal_project, tmp_path: Path):
    file_path = tmp_path / "roundtrip.json"
    minimal_project.save_to_file(file_path)
    assert file_path.exists()

    loaded = Project.load_from_file(file_path)
    assert loaded.metadata.title == minimal_project.metadata.title
    assert len(loaded.timeline.tracks) == len(minimal_project.timeline.tracks)
    assert loaded.duration_frames == minimal_project.duration_frames

