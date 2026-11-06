"""Video and audio transition models for HyperEdit Pro."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from hyperedit.core.models.transforms import InterpolationMode


class TransitionType(str, Enum):
    FADE = "fade"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    DIP_TO_BLACK = "dip_to_black"
    DIP_TO_WHITE = "dip_to_white"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


class TransitionAlignment(str, Enum):
    CENTER = "center"          # Transition spans across cut point evenly
    START_ON_CUT = "start_on_cut"  # Starts at cut point and transitions into next clip
    END_ON_CUT = "end_on_cut"      # Starts before cut point and ends exactly on cut


class Transition(BaseModel):
    """Transition definition between two adjacent clips."""

    type: TransitionType = Field(default=TransitionType.CROSSFADE)
    duration_frames: int = Field(default=15, gt=0, description="Duration in timeline frames")
    alignment: TransitionAlignment = Field(default=TransitionAlignment.CENTER)
    easing: InterpolationMode = Field(default=InterpolationMode.EASE_IN_OUT)
    custom_parameters: Optional[dict] = Field(default_factory=dict)

