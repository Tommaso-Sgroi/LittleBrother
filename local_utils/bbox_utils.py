from typing import Any

import numpy as np
from numpy import ndarray, dtype


def merge_overlapping_detections(detections: list, overlap_threshold: float = 0.3):
    """
    Merges overlapping bounding boxes based on Intersection over Union (IoU).

    Parameters:
        detections: List of bounding boxes to merge.
        overlap_threshold: IoU threshold for merging boxes. Boxes with IoU >= threshold are merged.

    Returns:
        list: List of merged bounding boxes.
    """
    if not detections:
        return []

    boxes = np.array(detections)
    x1, y1 = boxes[:, 0], boxes[:, 1]
    x2, y2 = boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    '''
    [     x      y    w      h   Area
        [ 1842   647  1926   771 10416]
        [ 1918   512  1947   575  1827]
        [ 1855   467  1912   635  9576]
     ]
    ------------------------
    [1842 1918 1855] all x1
    ------------------------
    [647 512 467] all y1
    ------------------------
    [1926 1947 1912] all x2
    ------------------------
    [771 575 635] all y2
    ------------------------
    [10625  1920  9802] all Area between them
    '''

    # Sort boxes by their area in descending order
    order = areas.argsort()[::-1]  # a[start:end:step]
    merged_boxes = []

    while len(order) > 0:
        i = order[0]
        merged_boxes.append(boxes[i])

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        inter = w * h
        union = areas[i] + areas[order[1:]] - inter
        iou = inter / union

        # Keep boxes with IoU below the threshold
        remain_indices = np.where(iou < overlap_threshold)[0] + 1
        order = order[remain_indices]

    return merged_boxes


def crop_bbox(frame: np.array, bbox: tuple[int, int, int, int]) -> np.ndarray:
    """
    Crops the frame based on the bounding box.
    :param frame: frame to crop.
    :param bbox: bbox to crop [x1, y1, x2, y2], NO AREA IS NEEDED.
    :return: the new frame cropped.

    bbox example: [1947,  475, 1954,  698, 1561]
    """
    # calculate width and height
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1

    cropped_frame = frame[y1:y1 + h, x1:x1 + w]
    return cropped_frame


def crop_bboxes(frame, bboxes: list[tuple[int, int, int, int]]) -> list[np.ndarray]:
    # cropped = []
    # for bbox in bboxes:
    #     cropped_frame = crop_bbox(frame, bbox)
    #     cropped.append(cropped_frame)
    return [
        crop_bbox(frame, bbox) for bbox in bboxes
    ]
