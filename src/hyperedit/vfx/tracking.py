"""Computer vision motion tracking and video stabilization engine."""

import math
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

from hyperedit.core.exceptions import MediaNotFoundError, MediaProbeError
from hyperedit.vfx.models import (
    PointTrack,
    RegionTrack,
    StabilizationTelemetry,
    TrackingMethod,
    TrackingTelemetry,
)


class MotionTracker:
    """Production-grade 2D motion tracker and stabilizer powered by OpenCV."""

    def __init__(self, confidence_threshold: float = 0.50) -> None:
        self.confidence_threshold = confidence_threshold

    def track_region(
        self,
        video_path: Path | str,
        initial_bbox: Tuple[float, float, float, float],
        method: TrackingMethod = TrackingMethod.REGION_TEMPLATE,
        max_frames: Optional[int] = None,
        search_padding_pct: float = 0.60,
    ) -> TrackingTelemetry:
        """Track a rectangular region across video frames.
        
        Args:
            video_path: Path to source video.
            initial_bbox: (x, y, width, height) in pixels on frame 0.
            method: Tracking algorithm (REGION_TEMPLATE or POINT_LK).
            max_frames: Optional frame limit.
            search_padding_pct: Neighborhood expansion ratio for template search.
        """
        path = Path(video_path).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Video file not found for tracking: {path}")

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise MediaProbeError(f"Failed to open video file for tracking: {path.name}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if max_frames:
            total_video_frames = min(total_video_frames, max_frames)

        ret, first_frame = cap.read()
        if not ret or first_frame is None:
            cap.release()
            raise MediaProbeError(f"Cannot read initial frame from {path.name}")

        h_img, w_img = first_frame.shape[:2]
        x0, y0, w0, h0 = initial_bbox
        x0, y0, w0, h0 = max(0.0, x0), max(0.0, y0), min(float(w_img - x0), w0), min(float(h_img - y0), h0)

        # Initial template
        ix, iy, iw, ih = int(round(x0)), int(round(y0)), int(round(w0)), int(round(h0))
        iw, ih = max(4, iw), max(4, ih)
        template = first_frame[iy : iy + ih, ix : ix + iw].copy()
        initial_template = template.copy()

        tracks: List[RegionTrack] = []
        # Record frame 0
        tracks.append(
            RegionTrack(
                frame_index=0,
                time_seconds=0.0,
                x=float(ix),
                y=float(iy),
                width=float(iw),
                height=float(ih),
                center_x=float(ix + iw / 2.0),
                center_y=float(iy + ih / 2.0),
                rotation_deg=0.0,
                scale=1.0,
                confidence=1.0,
                lost=False,
            )
        )

        curr_x, curr_y = float(ix), float(iy)
        frame_idx = 1
        lost_count = 0

        while True:
            if max_frames and frame_idx >= max_frames:
                break
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            t_sec = frame_idx / fps

            # Define localized search window around current predicted position
            pad_w = int(iw * search_padding_pct)
            pad_h = int(ih * search_padding_pct)
            sx1 = max(0, int(curr_x) - pad_w)
            sy1 = max(0, int(curr_y) - pad_h)
            sx2 = min(w_img, int(curr_x + iw) + pad_w)
            sy2 = min(h_img, int(curr_y + ih) + pad_h)

            search_region = frame[sy1:sy2, sx1:sx2]

            confidence = 0.0
            best_x, best_y = curr_x, curr_y
            is_lost = False

            if (
                search_region.shape[0] >= ih
                and search_region.shape[1] >= iw
                and template.shape[0] == ih
                and template.shape[1] == iw
            ):
                # Normalized cross correlation matching
                res = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                # TM_CCOEFF_NORMED produces score between -1 and 1
                confidence = float(max(0.0, min(1.0, max_val)))

                if confidence >= self.confidence_threshold:
                    best_x = float(sx1 + max_loc[0])
                    best_y = float(sy1 + max_loc[1])
                    curr_x, curr_y = best_x, best_y

                    # Update template with 5% adaptive blend to accommodate lighting shifts
                    new_sample = frame[int(best_y) : int(best_y + ih), int(best_x) : int(best_x + iw)]
                    if new_sample.shape == template.shape:
                        template = cv2.addWeighted(template, 0.95, new_sample, 0.05, 0)
                else:
                    # Low confidence detection: try initial template
                    res_orig = cv2.matchTemplate(search_region, initial_template, cv2.TM_CCOEFF_NORMED)
                    _, max_val_orig, _, max_loc_orig = cv2.minMaxLoc(res_orig)
                    if max_val_orig >= self.confidence_threshold:
                        confidence = float(max_val_orig)
                        best_x = float(sx1 + max_loc_orig[0])
                        best_y = float(sy1 + max_loc_orig[1])
                        curr_x, curr_y = best_x, best_y
                        template = initial_template.copy()
                    else:
                        is_lost = True
                        lost_count += 1
            else:
                is_lost = True
                lost_count += 1

            # Check viewport boundaries
            if curr_x < 0 or curr_y < 0 or (curr_x + iw) > w_img or (curr_y + ih) > h_img:
                is_lost = True

            tracks.append(
                RegionTrack(
                    frame_index=frame_idx,
                    time_seconds=round(t_sec, 4),
                    x=round(best_x, 2),
                    y=round(best_y, 2),
                    width=float(iw),
                    height=float(ih),
                    center_x=round(best_x + iw / 2.0, 2),
                    center_y=round(best_y + ih / 2.0, 2),
                    rotation_deg=0.0,
                    scale=1.0,
                    confidence=round(confidence, 4),
                    lost=is_lost,
                )
            )
            frame_idx += 1

        cap.release()

        total_tracked = len(tracks)
        confidences = [t.confidence for t in tracks if not t.lost]
        mean_conf = float(np.mean(confidences)) if confidences else 0.0

        return TrackingTelemetry(
            method=method,
            video_path=str(path),
            total_frames=total_tracked,
            tracked_frames=total_tracked - lost_count,
            lost_frames=lost_count,
            mean_confidence=round(mean_conf, 4),
            tracks=tracks,
            initial_bbox=initial_bbox,
        )

    def track_sparse_optical_flow(
        self,
        video_path: Path | str,
        initial_points: List[Tuple[float, float]],
        max_frames: Optional[int] = None,
    ) -> List[PointTrack]:
        """Track individual feature points using Lucas-Kanade optical flow with forward-backward check."""
        path = Path(video_path).resolve()
        if not path.is_file():
            raise MediaNotFoundError(f"Video file not found: {path}")

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise MediaProbeError(f"Cannot open video: {path.name}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        ret, prev_frame = cap.read()
        if not ret or prev_frame is None:
            cap.release()
            raise MediaProbeError("Failed to read first frame.")

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        p0 = np.array(initial_points, dtype=np.float32).reshape(-1, 1, 2)

        results: List[PointTrack] = []
        for i, (px, py) in enumerate(initial_points):
            results.append(PointTrack(frame_index=0, time_seconds=0.0, x=px, y=py, confidence=1.0, lost=False))

        frame_idx = 1
        curr_pts = p0

        lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )

        while True:
            if max_frames and frame_idx >= max_frames:
                break
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Forward LK
            p1, st, err = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, curr_pts, None, **lk_params)
            # Backward LK for consistency error validation
            p0_back, st_back, _ = cv2.calcOpticalFlowPyrLK(curr_gray, prev_gray, p1, None, **lk_params)

            t_sec = frame_idx / fps

            for i in range(len(curr_pts)):
                orig_pt = curr_pts[i][0]
                new_pt = p1[i][0]
                back_pt = p0_back[i][0]
                status = int(st[i][0])

                # Distance error between forward and backward flow
                fb_error = float(np.linalg.norm(orig_pt - back_pt))
                conf = max(0.0, min(1.0, 1.0 - (fb_error / 10.0)))
                lost = status != 1 or fb_error > 5.0

                results.append(
                    PointTrack(
                        frame_index=frame_idx,
                        time_seconds=round(t_sec, 4),
                        x=round(float(new_pt[0]), 2),
                        y=round(float(new_pt[1]), 2),
                        confidence=round(conf, 4),
                        lost=lost,
                    )
                )

            curr_pts = p1
            prev_gray = curr_gray
            frame_idx += 1

        cap.release()
        return results

    def stabilize_video(
        self,
        video_path: Path | str,
        output_path: Path | str,
        smoothing_window: int = 15,
        crop_border_pct: float = 0.05,
    ) -> StabilizationTelemetry:
        """Stabilize camera jitter using estimated 2D affine trajectory and Gaussian smoothing."""
        src_path = Path(video_path).resolve()
        dst_path = Path(output_path).resolve()
        dst_path.parent.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(src_path))
        if not cap.isOpened():
            raise MediaProbeError(f"Cannot open video for stabilization: {src_path.name}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        ret, prev_frame = cap.read()
        if not ret or prev_frame is None:
            cap.release()
            raise MediaProbeError("Empty video for stabilization.")

        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        # 1. Evaluate frame-to-frame transforms (dx, dy, da)
        transforms: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
        all_frames: List[np.ndarray] = [prev_frame]

        feature_params = dict(maxCorners=200, qualityLevel=0.01, minDistance=30, blockSize=3)
        lk_params = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            all_frames.append(frame)

            curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            p0 = cv2.goodFeaturesToTrack(prev_gray, mask=None, **feature_params)

            dx, dy, da = 0.0, 0.0, 0.0
            if p0 is not None and len(p0) >= 8:
                p1, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, p0, None, **lk_params)
                good_old = p0[st == 1]
                good_new = p1[st == 1]

                if len(good_old) >= 6:
                    m, _ = cv2.estimateAffinePartial2D(good_old, good_new)
                    if m is not None:
                        dx = float(m[0, 2])
                        dy = float(m[1, 2])
                        da = float(math.atan2(m[1, 0], m[0, 0]))

            transforms.append((dx, dy, da))
            prev_gray = curr_gray

        cap.release()

        # 2. Integrate to trajectory (X, Y, A)
        trajectory = np.zeros((len(transforms), 3), dtype=np.float64)
        for i in range(1, len(transforms)):
            trajectory[i] = trajectory[i - 1] + np.array(transforms[i])

        # 3. Smooth trajectory with moving box / Gaussian filter
        smoothed_traj = np.copy(trajectory)
        radius = max(1, smoothing_window // 2)
        for i in range(len(trajectory)):
            start_idx = max(0, i - radius)
            end_idx = min(len(trajectory), i + radius + 1)
            smoothed_traj[i] = np.mean(trajectory[start_idx:end_idx], axis=0)

        # 4. Difference gives compensation warp (diff = smoothed - trajectory)
        diff = smoothed_traj - trajectory

        displacements = [float(np.linalg.norm(diff[i, :2])) for i in range(len(diff))]
        max_disp = max(displacements) if displacements else 0.0
        mean_disp = float(np.mean(displacements)) if displacements else 0.0

        # 5. Render stabilized frames to destination video
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out_writer = cv2.VideoWriter(str(dst_path), fourcc, fps, (width, height))

        crop_x = int(width * crop_border_pct)
        crop_y = int(height * crop_border_pct)
        crop_w = width - 2 * crop_x
        crop_h = height - 2 * crop_y

        for i, frame in enumerate(all_frames):
            dx_comp = diff[i, 0]
            dy_comp = diff[i, 1]
            da_comp = diff[i, 2]

            # Reconstruct compensation affine matrix
            cos_a = math.cos(da_comp)
            sin_a = math.sin(da_comp)

            # Center of frame for rotation
            cx, cy = width / 2.0, height / 2.0
            M = np.zeros((2, 3), dtype=np.float32)
            M[0, 0] = cos_a
            M[0, 1] = -sin_a
            M[1, 0] = sin_a
            M[1, 1] = cos_a
            M[0, 2] = dx_comp + (1 - cos_a) * cx + sin_a * cy
            M[1, 2] = dy_comp - sin_a * cx + (1 - cos_a) * cy

            # Apply stabilization warp with border replication
            stabilized = cv2.warpAffine(frame, M, (width, height), borderMode=cv2.BORDER_REFLECT)

            # Zoom crop to remove black edges from stabilization movement
            cropped = stabilized[crop_y : crop_y + crop_h, crop_x : crop_x + crop_w]
            final_frame = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LINEAR)
            out_writer.write(final_frame)

        out_writer.release()

        return StabilizationTelemetry(
            total_frames=len(all_frames),
            max_displacement_px=round(max_disp, 2),
            mean_displacement_px=round(mean_disp, 2),
            crop_margin_pct=crop_border_pct,
            smoothed_trajectory=[(round(float(d[0]), 2), round(float(d[1]), 2), round(float(d[2]), 4)) for d in diff],
        )

