"""Pytest fixtures and configuration for HyperEdit Pro."""

import pytest

from hyperedit.core.models.project import Project


@pytest.fixture
def minimal_project_dict():
    return {
        "schema_version": "2.0.0",
        "metadata": {
            "title": "Pytest Demo Project",
            "description": "Used in automated test fixtures",
            "author": "Pytest"
        },
        "settings": {
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "sample_rate": 48000,
            "audio_channels": 2,
            "color_space": "bt709",
            "working_pixel_format": "yuv420p"
        },
        "media_pool": {
            "assets": {
                "test_vid": {
                    "asset_id": "test_vid",
                    "file_path": "fixtures/sample.mp4",
                    "format_name": "mp4",
                    "duration_seconds": 10.0,
                    "size_bytes": 1024,
                    "video_streams": [
                        {
                            "index": 0,
                            "codec": "h264",
                            "width": 1920,
                            "height": 1080,
                            "fps": 30.0,
                            "duration_seconds": 10.0
                        }
                    ],
                    "audio_streams": []
                }
            }
        },
        "timeline": {
            "tracks": [
                {
                    "track_id": "V1",
                    "name": "Video",
                    "kind": "video",
                    "index": 0,
                    "clips": [
                        {
                            "clip_id": "c1",
                            "asset_id": "test_vid",
                            "in_frame": 0,
                            "out_frame": 150,
                            "timeline_start_frame": 0
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture
def minimal_project(minimal_project_dict):
    return Project.model_validate(minimal_project_dict)

