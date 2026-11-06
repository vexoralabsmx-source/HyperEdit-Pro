"""Spatial motion, keyframing, virtual camera, and Ken Burns engine for HyperEdit Pro."""

from typing import Dict, List

from hyperedit.core.models.timeline import Clip
from hyperedit.core.models.transforms import (
    AnimatedProperty,
    InterpolationMode,
    Keyframe,
    Transform,
)
from hyperedit.core.protocols import MotionEngineProtocol
from hyperedit.motion.interpolator import KeyframeInterpolator


class MotionEngine(MotionEngineProtocol):
    """Calculates spatial transformations, camera moves, and compiles FFmpeg motion filtergraphs."""

    def interpolate_transform(self, clip: Clip, current_frame: int) -> Dict[str, float]:
        """Calculate spatial transform parameters at a specific frame index along the clip timeline."""
        if not clip.transform:
            return {
                "position_x": 0.0,
                "position_y": 0.0,
                "scale_x": 1.0,
                "scale_y": 1.0,
                "rotation_deg": 0.0,
                "opacity": 1.0,
                "crop_top": 0.0,
                "crop_bottom": 0.0,
                "crop_left": 0.0,
                "crop_right": 0.0,
            }

        t = clip.transform
        rel_frame = max(0, current_frame - clip.timeline_start_frame)

        # Base values
        result: Dict[str, float] = {
            "position_x": t.position_x,
            "position_y": t.position_y,
            "scale_x": t.scale_x,
            "scale_y": t.scale_y,
            "rotation_deg": t.rotation_deg,
            "opacity": t.opacity,
            "crop_top": t.crop_top,
            "crop_bottom": t.crop_bottom,
            "crop_left": t.crop_left,
            "crop_right": t.crop_right,
        }

        # Override with keyframed properties if present
        for anim in t.animated:
            prop_val = KeyframeInterpolator.evaluate(anim, rel_frame)
            if anim.property_name in result:
                result[anim.property_name] = prop_val
            elif anim.property_name == "scale":
                result["scale_x"] = prop_val
                result["scale_y"] = prop_val

        return result

    def build_video_filter(self, clip: Clip, target_w: int, target_h: int) -> str:
        """Compile static or keyframed spatial transforms into FFmpeg scale, crop, and pad filter string."""
        if not clip.transform:
            return f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"

        t = clip.transform
        scale_x = t.scale_x
        scale_y = t.scale_y
        opacity = t.opacity

        filters: List[str] = []

        # Scaling
        scaled_w = int(round(target_w * scale_x))
        # Ensure even pixel dimensions for H.264
        scaled_w = scaled_w if scaled_w % 2 == 0 else scaled_w + 1
        scaled_h = int(round(target_h * scale_y))
        scaled_h = scaled_h if scaled_h % 2 == 0 else scaled_h + 1

        filters.append(f"scale={scaled_w}:{scaled_h}")

        # Opacity / Colorchannelmixer
        if opacity < 0.999:
            filters.append(f"colorchannelmixer=aa={opacity:.3f}")

        # Positioning & Padding to canvas
        pos_x = int(round(t.position_x))
        pos_y = int(round(t.position_y))
        filters.append(f"pad={target_w}:{target_h}:(ow-iw)/2+{pos_x}:(oh-ih)/2+{pos_y}:color=black@0.0")

        return ",".join(filters)

    def apply_ken_burns(
        self,
        clip: Clip,
        start_scale: float = 1.0,
        end_scale: float = 1.12,
        start_pan_x: float = 0.0,
        end_pan_x: float = 0.0,
        start_pan_y: float = 0.0,
        end_pan_y: float = 0.0,
        mode: InterpolationMode = InterpolationMode.EASE_IN_OUT,
    ) -> Clip:
        """Apply a smooth, cinematic Ken Burns pan-and-zoom trajectory across the clip duration."""
        dur_frames = clip.timeline_duration_frames
        if dur_frames <= 1:
            return clip

        if not clip.transform:
            clip.transform = Transform()

        # Animate scale
        scale_anim = AnimatedProperty(
            property_name="scale",
            base_value=start_scale,
            keyframes=[
                Keyframe(frame=0, value=start_scale, interpolation=mode),
                Keyframe(frame=dur_frames, value=end_scale, interpolation=mode),
            ],
        )

        # Animate Pan X if specified
        x_anim = AnimatedProperty(
            property_name="position_x",
            base_value=start_pan_x,
            keyframes=[
                Keyframe(frame=0, value=start_pan_x, interpolation=mode),
                Keyframe(frame=dur_frames, value=end_pan_x, interpolation=mode),
            ],
        )

        # Animate Pan Y if specified
        y_anim = AnimatedProperty(
            property_name="position_y",
            base_value=start_pan_y,
            keyframes=[
                Keyframe(frame=0, value=start_pan_y, interpolation=mode),
                Keyframe(frame=dur_frames, value=end_pan_y, interpolation=mode),
            ],
        )

        clip.transform.animated = [scale_anim, x_anim, y_anim]
        return clip

    def apply_beat_reactive_pulsing(
        self,
        clip: Clip,
        beat_timestamps_sec: List[float],
        fps: float = 30.0,
        pulse_scale: float = 1.08,
    ) -> Clip:
        """Generate audio-reactive scale pulsation keyframes synchronized to musical beats."""
        if not clip.transform:
            clip.transform = Transform()

        clip_start_sec = clip.timeline_start_frame / fps
        clip_end_sec = clip.timeline_end_frame / fps

        kfs: List[Keyframe] = []
        # Filter beats occurring during this clip
        clip_beats = [t for t in beat_timestamps_sec if clip_start_sec <= t <= clip_end_sec]

        for b_time in clip_beats:
            rel_sec = b_time - clip_start_sec
            hit_frame = int(round(rel_sec * fps))

            # Pulse: Quick 2-frame attack up, 6-frame decay down to 1.0
            pre_frame = max(0, hit_frame - 1)
            peak_frame = hit_frame + 2
            decay_frame = hit_frame + 8

            kfs.append(Keyframe(frame=pre_frame, value=1.0, interpolation=InterpolationMode.EASE_OUT))
            kfs.append(Keyframe(frame=peak_frame, value=pulse_scale, interpolation=InterpolationMode.EASE_IN))
            kfs.append(Keyframe(frame=decay_frame, value=1.0, interpolation=InterpolationMode.LINEAR))

        kfs.sort(key=lambda k: k.frame)
        scale_prop = AnimatedProperty(
            property_name="scale",
            base_value=1.0,
            keyframes=kfs,
        )
        clip.transform.animated.append(scale_prop)
        return clip

