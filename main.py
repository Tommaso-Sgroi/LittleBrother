import multiprocessing
import time
from multiprocessing import Queue
from typing import Union

import cv2
import torch

from camera.frame_controller import VideoFrameController
from camera.frame_source import QueuedFrameSource
from face_recognizer.face_recognizer import FaceRecognizer
from local_utils.logger import get_logger
from local_utils.view import view

logger = get_logger(__name__)







def start_video_processing(sources: list[multiprocessing.Process], queue:multiprocessing.Queue):
    processes = []

    # for vp in sources:
    #     p = multiprocessing.Process(target=process_video_frames, args=(vp,), )
    #     processes.append(p)
    #     p.start()
    return processes

def initialize_frame_controller(sources: list[Union[str, int]],
                                yolo_model_name:str,
                                max_queue_size:int=None,
                                fps:int=15,
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
    from main.video_processor import VideoProcessorFrameControllerFactory

    vpfcf = VideoProcessorFrameControllerFactory()
    controller = vpfcf.initializer( sources,
                                    yolo=yolo_model_name,
                                    max_queue_size=max_queue_size,
                                    fps=fps,
                                    **kwargs)
    return controller


def terminate_video_processing(processes):
    logger.info("[main] Terminating children...")
    for p in processes:
        p.terminate()

    for p in processes:
        p.join(timeout=1)
        if p.is_alive():
            logger.critical("[main] Forcing kill on", p.pid)
            p.kill()




if __name__ == "__main__":
    video_paths = [
        0,
        # 'datasets/SamsungGear360.mp4'
    ]

    frame_controller = initialize_frame_controller(video_paths, fps=30, yolo_model_name='yolo11n', scale_size=50)
    # vc = cv2.VideoCapture(0)
    # for i in range(1000):
    #     ret, frame = vc.read()
    #     view(frame, scale=1)
    # quit()
    frame_controller.start()
    from time import sleep

    while True:
        sleep(1)
        sourceids_frames = frame_controller.get_frames()
        # [frame_source_id, ('label', frame)]
        if len(sourceids_frames) > 0:
            pass
        print('Aiuto')
        for label, frame in sourceids_frames:
            print(label, frame)
            view(frame, winname=label)

