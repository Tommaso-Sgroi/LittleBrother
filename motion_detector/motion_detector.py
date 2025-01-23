from typing import Any

import cv2 as cv
import numpy as np
from cv2 import Mat
from numpy import ndarray
from utils.bbox_utils import merge_overlapping_detections


def detect_moving_objects(frame: np.ndarray, background_subtractor: cv.BackgroundSubtractor,
                          area_threshold: int = 100) -> tuple[list[list[int]], Mat | ndarray]:
    """
    Detects moving objects using a background subtractor, returns their bounding boxes.

    Parameters:
        frame: Current video frame.
        background_subtractor: Background subtractor for motion detection.
        area_threshold: Minimum area for detected bounding boxes.


    Returns:
        List of detected bounding boxes with their areas, [x1, y1, x2, y2, area]

    Notes:
        - https://medium.com/analytics-vidhya/opencv-findcontours-detailed-guide-692ee19eeb18
    """

    fg_mask = background_subtractor.apply(frame)
    contours, _ = cv.findContours(fg_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    detections = []
    for cnt in contours:
        x, y, w, h = cv.boundingRect(cnt)
        area = w * h
        if area > area_threshold:
            detections.append([x, y, x + w, y + h, area])

    return detections, fg_mask


def mog2_movement_detection(frame: np.ndarray, *, background_subtractor: cv.BackgroundSubtractor,
                            area_threshold: int = 100, overlap_threshold=0.0, draw=False) -> tuple[
    Any, list, np.ndarray]:
    detections, _ = detect_moving_objects(frame, background_subtractor, area_threshold=area_threshold)
    merged_detections = merge_overlapping_detections(detections, overlap_threshold)

    # Draw bounding boxes
    if draw:
        for det in merged_detections:
            x1, y1, x2, y2, _ = det
            cv.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    return detections, merged_detections, frame
