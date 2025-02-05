from typing import Any

import numpy as np
from ultralytics import YOLO

from local_utils.logger import Logger


class PeopleDetector(YOLO, Logger):
    """
    0: 320x640 1 person, 1 umbrella, 3 chairs, 1 couch, 3 potted plants, 2 tvs, 21.1ms
    Speed: 1.2ms preprocess, 21.1ms inference, 1.1ms postprocess per image at shape (1, 3, 320, 640)
    [ultralytics.engine.results.Results object with attributes:

    boxes: ultralytics.engine.results.Boxes object
    keypoints: None
    masks: None
    names: {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee', 30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'}
    obb: None
    orig_img: array([[[  0,   1,   1],
        [ 93, 102, 103],
        [ 93, 102, 103],
    """

    def __init__(self, model_name, threshold=0.25, verbose=False, **kwargs):
        YOLO.__init__(self, model_name, **kwargs)
        Logger.__init__(self, f'{model_name}')
        self.focus_on_classes = [0]
        self.threshold = threshold
        self.verbose = verbose

    def detect(self, frame: np.ndarray) -> tuple[Any, Any, Any]:
        """
        :param frame: frame in which detect people
        :return: a np.array of the confidences scores, a np.array of the bounding box coordinates, and the result obj
        """
        results = \
        self(frame, classes=self.focus_on_classes, conf=self.threshold, device=self.device, verbose=self.verbose)[
            0]  # list of 1 Results object, because we can predict in batches (for video only)
        """
        cls: tensor([0., 0., 0., 0., 0., 0.], device='cuda:0')
        conf: tensor([0.9429, 0.9262, 0.8841, 0.8833, 0.8824, 0.8773], device='cuda:0')
        xywh: tensor([
            [1207.5342,  576.8246,  510.5572,  977.0013],
            [ 447.3520,  351.2901,  267.4479,  537.2728],
            [ 709.4022,  370.9929,  235.7747,  489.7085],
            [ 317.8023,  557.6183,  408.7670,  422.3871],
            [1684.3063,  498.2565,  354.5173,  403.8601],
            [1512.9242,  217.1133,  132.6541,  321.3105]
        ])
        """
        probs, bboxes = results.boxes.conf, results.boxes.xywh
        probs = probs.cpu().numpy()
        bboxes = bboxes.cpu().numpy()
        if len(probs) > 0:
            self.logger.debug('%s people found with accuracy %s', str(len(probs)), ", ".join(f"{p:.3f}" for p in probs.tolist()))
        else:
            self.logger.debug('no person has been detected')
        return probs, bboxes, results

    def detect_on_frames(self, frames: list[np.ndarray]) -> list[tuple[Any, Any, Any]]:
        return [
            self.detect(frame) for frame in frames
        ]
