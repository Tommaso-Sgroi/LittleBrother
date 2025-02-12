from multiprocessing import Queue
from typing import Union

import torch
from ultralytics import YOLO
from camera.frame_controller import VideoFrameController
from camera.frame_source import QueuedFrameSource, FrameSource
from camera.video_frame_initializer import QueuedFrameControllerFactory
from face_recognizer.face_recognizer import FaceRecognizer
from local_utils.config import VideoFrameControllerConfig, VideoFrameSourceConfig
from local_utils.frames import rescale_frame
from local_utils.view import view
from motion_detector.motion_detector import MotionDetector


class VideoProcessor(QueuedFrameSource):

    def __init__(self, id, *,
                 source: Union[int, str],
                 name: str = None,
                 yolo: str,
                 face_recogniser_threshold=0.5,
                 motion_detector_threshold= 0.5,
                 motion_detector_min_area=500,
                 motion_detector= "mog2",
                 scale_size=100,
                 batch_size: int = 1,
                 fifo_queue: Queue,
                 timeout=0.1,
                 fps=30,
                 device=None,
                 view: bool=False
                 ):
        super().__init__(id, source, fifo_queue, timeout, fps, daemon=False)
        self.name = name if name is not None else f"VideoProcessor-{id}"
        self.source = source
        self.device = (
            "cuda" if torch.cuda.is_available()
            else ("mps" if torch.backends.mps.is_available() else "cpu")
        ) if device is None else device
        self.motion_detector = None
        self.yolo_model_name = yolo
        self.yolo_model = None
        self.face_recognizer = None
        self.face_recogniser_threshold = face_recogniser_threshold
        self.batch_size = batch_size
        self.scale_size = scale_size
        self.view = view
        self.motion_detector_threshold = motion_detector_threshold
        self.motion_detector_min_area = motion_detector_min_area
        self.motion_detector_name = motion_detector

    def run(self):
        self.motion_detector = MotionDetector(detector=self.motion_detector_name, threshold=self.motion_detector_threshold, min_area=self.motion_detector_min_area)
        self.yolo_model = YOLO(self.yolo_model_name)
        self.face_recognizer = FaceRecognizer(threshold=self.face_recogniser_threshold)
        super().run()

    def next(self):
        frames = []
        try:
            for _ in range(self.batch_size):
                frame = super().next()
                frames.append(frame)
        except StopIteration:
            if len(frames) == 0:
                # do not discard the last frames
                self.logger.info(f"[%s] end of video reached.", self.id)
                raise StopIteration('end of video reached')
        return frames

    def queue_video_frame(self, frames):
        # put the frames in the queue
        detection = self.process_video_frames(frames)
        # detection: list[Union[int, str], list[str, tuple[str, str]]]
        if len(detection) > 0:
            self.queue.put([detection], timeout=self.timeout)

    def process_video_frames(self, frames) -> list[list[int, str, str]]:
        # Each process gets its own model and face recognizer
        batch_frames = [rescale_frame(frame, self.scale_size) for frame in
                        frames if self.motion_detector(frame)]  # Resize the frame to 50% of its original size

        if len(batch_frames) == 0:
            return []

        # When the batch is full or end-of-video is reached, process the batch.
        results = self.yolo_model(
            batch_frames, classes=[0], device=self.device, verbose=False
        )

        if self.view:
            self.view_frames([result.plot() for result in results], winname=str(self.id) + ': yolo')

        label_index, detections = 1, []
        for result, frame in zip(results, batch_frames):
            detect = [self.id, None, frame] # id, label, frame
            boxes = result.boxes.xyxy.type(torch.int32)
            for box in boxes:
                x1, y1, x2, y2 = box
                if x2 - x1 < 20 or y2 - y1 < 20: continue

                detected_person_image = frame[y1:y2, x1:x2]

                faces = self.face_recognizer.recognize_faces(detected_person_image)
                if len(faces) == 0:
                    detections.append(detect)
                    continue

                for detected_face in faces:
                    face_detected = detected_face["label"]
                    if face_detected is not None:
                        detect[label_index] = face_detected
                        detections.append(detect)
                        self.logger.debug(
                            "[%s] Detected face: %s with confidence %s", self.id, face_detected, detected_face['confidence']
                        )
                    else:
                        detections.append(detect)
        return detections

    def view_frames(self, batch_frames, winname):
        for frame in batch_frames:
            view(frame, winname=winname)


class VideoProcessorFrameControllerFactory(QueuedFrameControllerFactory):
    """
    A factory for creating `VideoProcessor` sources. Inherits from
    `QueuedFrameControllerFactory` and overrides `build_source` to produce
    instances of `VideoProcessor` for either a camera device (int) or a video file (str).
    """

    def initializer(self, config: VideoFrameControllerConfig) -> VideoFrameController:
        return super().initializer(config)

    def build_source(self, source:VideoFrameSourceConfig, **kwargs) -> FrameSource:
        if not isinstance(source.source, int) and not isinstance(source.source, str):
            raise ValueError(f"Invalid source type: {type(source)}")
        args = source.to_dict()
        return VideoProcessor(**args, **kwargs)


def initialize_frame_controller(config: VideoFrameControllerConfig) -> VideoFrameController:
    """
    Initialize the frame controller with the given configuration.
    """
    vpfcf = VideoProcessorFrameControllerFactory()

    controller = vpfcf.initializer(config)
    return controller
