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
from main.video_processor import initialize_frame_controller

logger = get_logger(__name__)







def start_video_processing(sources: list[multiprocessing.Process], queue:multiprocessing.Queue):
    processes = []

    # for vp in sources:
    #     p = multiprocessing.Process(target=process_video_frames, args=(vp,), )
    #     processes.append(p)
    #     p.start()
    return processes

def initialize_camera_resources(video_paths: list[Union[str, int]]) -> VideoFrameController:
    """
    Initializes the camera resources and returns the video frame initializer.
    args:
        video_paths: A list of video paths or camera IDs.
    returns:
    """
    from camera.video_frame_initializer import initializer

    return initializer(video_paths)


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
        # 0,
        'datasets/SamsungGear360.mp4'
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

