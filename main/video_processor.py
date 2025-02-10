import time
from multiprocessing import Queue
from typing import Union

import torch
from ultralytics import YOLO
from camera.frame_controller import VideoFrameController
from camera.frame_source import QueuedFrameSource, FrameSource
from camera.video_frame_initializer import QueuedFrameControllerFactory
from face_recognizer.face_recognizer import FaceRecognizer
from local_utils.frames import rescale_frame
from local_utils.view import view
from motion_detector.motion_detector import MotionDetector


class VideoProcessor(QueuedFrameSource):

    def __init__(self, id, *,
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
                 view=False):
        super().__init__(id, fifo_queue, timeout, fps, daemon=False)
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
        self.motion_detector = motion_detector

    def run(self):
        self.motion_detector = MotionDetector(detector=self.motion_detector, threshold=self.motion_detector_threshold, min_area=self.motion_detector_min_area)
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
                self.logger.info(f"[{self.id}] end of video reached.")
                raise StopIteration('end of video reached')
        return frames

    def queue_video_frame(self, frames):
        # put the frames in the queue
        detection = self.process_video_frames(frames)
        # detection: list[Union[int, str], list[str, tuple[str, str]]]
        if len(detection) > 0:
            self.queue.put([detection], timeout=self.timeout)

    def process_video_frames(self, frames) -> list[Union[str, tuple[str, str]]]:
        # Each process gets its own model and face recognizer

        start_time = time.time()
        frame_count = 0

        batch_frames = [rescale_frame(frame, self.scale_size) for frame in
                        frames if self.motion_detector(frame)]  # Resize the frame to 50% of its original size
        frame_count += 1

        if len(batch_frames) == 0:
            return []

        # When the batch is full or end-of-video is reached, process the batch.
        results = self.yolo_model(
            batch_frames, classes=[0], device=self.device, verbose=False
        )

        detections = []
        if self.view:
            annotated_batch_frames = [result.plot() for result in results]
            self.view_frames(annotated_batch_frames, winname=str(self.id) + ' yolo')

        index = 0
        for result, frame in zip(results, batch_frames):
            boxes = result.boxes.xyxy.type(torch.int32)
            for box in boxes:
                x1, y1, x2, y2 = box
                if x2 - x1 < 20 or y2 - y1 < 20: continue

                detected_person_image = frame[y1:y2, x1:x2]

                faces = self.face_recognizer.recognize_faces(detected_person_image)
                if len(faces) == 0:
                    detections.append((self.id, None, frame))

                for detected_face in faces:
                    if detected_face["label"] is not None:
                        detections.append((self.id, detected_face["label"], frame))
                        self.logger.debug(
                            f"[{self.id}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                        )
                    else:
                        detections.append((self.id, None, frame))
            index += 1

        total_time = time.time() - start_time
        average_fps = frame_count / total_time if total_time > 0 else 0
        # print(f"\n[{self.id}] Average FPS: {average_fps:.2f}")
        # print(f"[{self.id}] Total frames: {frame_count}")
        # print(f"[{self.id}] Total time: {total_time:.2f}s\n")

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

    def initializer(self, sources: list[Union[str, int]], max_queue_size=None, fps=15,
                    **kwargs) -> VideoFrameController:
        """
        Build a `VideoProcessor` instance for the given source.

        This method expects `source` to be either an integer representing
        the ID of a camera device or a string representing the path to a
        video file. Additional keyword arguments (e.g., YOLO model, threshold,
        etc.) are forwarded to the `VideoProcessor` constructor.

        Args:
            sources (Union[str, int]):
                - If `int`, the camera device index from which to read frames.
                - If `str`, a path to a video file on the filesystem.
            max_queue_size `int`: Maximum number of frames to buffer in the queue (per source).
            fps `int`: Desired frames per second for reading from each source.

            **kwargs:
                Additional parameters that are passed directly to the
                `VideoProcessor` constructor. Common options include:
                - yolo (str): Path or identifier of the YOLO model.

                [optional]:
                - face_recogniser_threshold (float): Threshold for face recognition, defaults to 0.5.
                - scale_size (int): Desired scale size for processing (default, 100 which means 'no scale', alias: 100% of the image).
                - batch_size (int): Number of frames to batch process, defaults to 1.
                - timeout (float): Timeout in seconds for queue operations, defaults to 0.1, in FrameSource raise queue.Full and skip the frame, in FrameController raise queue.Empty.
                - fps (int): Desired frames per second, defaults to 30.
                - device (str): Hardware device to run processing on (default device is cuda if available, mps if available, else cpu).
                - view (bool): If True, it shows the captured frames and yolo's annotated frames.
        Returns:
            FrameSource:
                A newly created `VideoProcessor` instance that inherits from `QueuedFrameSource`.

        Raises:
            ValueError:
                If `source` is neither an integer nor a string.
        """
        return super().initializer(sources, max_queue_size, fps, **kwargs)

    def build_source(self, source: Union[str, int], **kwargs) -> FrameSource:
        if not isinstance(source, int) and not isinstance(source, str):
            raise ValueError(f"Invalid source type: {type(source)}")

        return VideoProcessor(source, **kwargs)


def initialize_frame_controller(sources: list[Union[str, int]],
                                yolo_model_name: str,
                                max_queue_size: int = None,
                                fps: int = 15,
                                **kwargs) -> VideoFrameController:
    """
    Initializes the camera resources and returns the video frame initializer.
        Args:
            sources (Union[str, int]):
                - If `int`, the camera device index from which to read frames.
                - If `str`, a path to a video file on the filesystem.
            max_queue_size: Maximum number of frames to buffer in the queue (per source).
            yolo_model_name (str): Name of the YOLO model to use for object detection.
            fps: Desired frames per second for reading from each source.


            **kwargs:
                Additional parameters that are passed directly to the
                `VideoProcessor` constructor. Common options include:
                - id (int): Unique identifier for the source, it is the path of a video stream or an integer for a camera stream, used by opencv.VideoStream.
                - yolo (str): Path or identifier of the YOLO model.

                [optional]:
                - face_recogniser_threshold (float): Threshold for face recognition, defaults to 0.5.
                - scale_size (int): Desired scale size for processing (default, 100 which means 'no scale', alias: 100% of the image).
                - batch_size (int): Number of frames to batch process, defaults to 1.
                - timeout (float): Timeout in seconds for queue operations, defaults to 0.1, in FrameSource raise queue.Full and skip the frame, in FrameController raise queue.Empty.
                - fps (int): Desired frames per second, defaults to 30.
                - device (str): Hardware device to run processing on (default device is cuda if available, mps if available, else cpu).
                - view (bool): If True, it shows the captured frames and yolo's annotated frames.
        Returns:
            VideoFrameController:
                A newly created `VideoFrameController` containing all QueuedFrameSource.
    """
    vpfcf = VideoProcessorFrameControllerFactory()
    controller = vpfcf.initializer(sources,
                                   yolo=yolo_model_name,
                                   max_queue_size=max_queue_size,
                                   fps=fps,
                                   **kwargs)
    return controller
