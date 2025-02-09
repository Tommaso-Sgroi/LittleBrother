import cv2 as cv
import numpy as np

from local_utils.logger import Logger


class MotionDetector(Logger):
    def __init__(
            self, detector: str = "mog2", threshold: float = 0.1, min_area: int = 500
    ):
        super().__init__(self.__class__.__name__)
        self.detector = detector.lower()
        if self.detector == "mog2":
            self.bg_subtractor = cv.createBackgroundSubtractorMOG2(
                history=10, detectShadows=False
            )
            self.min_area = min_area
            self.logger.debug(
                "Initialized MOG2 detector with history=10 and min_area=%s", min_area
            )
        elif self.detector == "optical_flow":
            self.threshold = threshold
            self.logger.debug(
                "Initialized Optical Flow detector with threshold=%s", threshold
            )
        else:
            raise ValueError(
                "Unsupported detector type. Choose 'mog2' or 'optical_flow'."
            )

    def detect(self, *frames: np.ndarray) -> bool:
        """
        Detect motion using the selected method.

        For 'mog2', provide a single frame.
        For 'optical_flow', provide two frames: previous and current.
        """
        if self.detector == "mog2":
            if len(frames) != 1:
                raise ValueError("MOG2 detector requires exactly one frame.")
            result = self._mog2_motion_detector(frames[0])
            self.logger.debug("MOG2 detection result: %s", result)
            return result
        elif self.detector == "optical_flow":
            if len(frames) != 2:
                raise ValueError(
                    "Optical Flow detector requires previous and current frames."
                )
            result = self._optical_flow_motion_detector(frames[0], frames[1])
            self.logger.debug("Optical Flow detection result: %s", result)
            return result

    def _mog2_motion_detector(self, frame: np.ndarray) -> bool:
        """Internal method for motion detection using MOG2."""
        mask = self.bg_subtractor.apply(frame)
        contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv.contourArea(cnt) > self.min_area:
                return True
        return False

    def _optical_flow_motion_detector(
            self, prev_frame: np.ndarray, curr_frame: np.ndarray
    ) -> bool:
        """Internal method for motion detection using optical flow."""
        prev_gray = cv.cvtColor(prev_frame, cv.COLOR_BGR2GRAY)
        curr_gray = cv.cvtColor(curr_frame, cv.COLOR_BGR2GRAY)
        flow = cv.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        mag, _ = cv.cartToPolar(flow[..., 0], flow[..., 1])
        return mag.mean() > self.threshold

    def __call__(self, *frames: np.ndarray) -> bool:
        """Allow the instance to be called as a function to detect motion."""
        return self.detect(*frames)
