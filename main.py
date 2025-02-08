import multiprocessing
import time
from abc import ABC
from multiprocessing import Queue
from typing import Union

import cv2
import torch
from ultralytics import YOLO

from camera.frame_controller import VideoFrameController
from camera.frame_source import QueuedFrameSource
from face_recognizer.face_recognizer import FaceRecognizer
from local_utils.logger import get_logger
from local_utils.view import view

logger = get_logger(__name__)

def rescale_frame(frame, percent=50):
    percent = 1 - (percent / 100)
    if percent == 0: return frame

    width = int(frame.shape[1] * percent)
    height = int(frame.shape[0] * percent)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

class VideoProcessor(QueuedFrameSource):

    def __init__(self, id, yolo: str, *,
                 face_recogniser_threshold = 0.5,
                 scale_size=0,
                 batch_size:int= 1,
                 fifo_queue: multiprocessing.Queue,
                 timeout=0.1,
                 fps=30,
                 device=None,):
        super().__init__(id, fifo_queue, timeout, fps, stream=None, daemon=False)
        self.device = (
            "cuda" if torch.cuda.is_available()
            else ("mps" if torch.backends.mps.is_available() else "cpu")
        ) if device is None else device
        self.yolo_model_name = yolo
        self.yolo_model = None
        self.face_recognizer = None
        self.face_recogniser_threshold = face_recogniser_threshold
        self.batch_size = batch_size
        self.scale_size = scale_size


    def queue_video_frame(self, frames):
        detection = self.process_video_frames(frames)
        if len(detection) > 1:
            self.queue.put(detection, timeout=self.timeout)

    def run(self):
        self.yolo_model = YOLO(self.yolo_model_name)
        self.face_recognizer = FaceRecognizer(threshold=self.face_recogniser_threshold)
        super().run()

    def next(self):
        frames = []
        for _ in range(self.batch_size):
            frame = super().next()
            frames.append(frame)
        # self.process_video_frames(frames)
        return frames

    def process_video_frames(self, frames):
        # Each process gets its own model and face recognizer

        start_time = time.time()
        frame_count = 0

        batch_frames = [rescale_frame(frame, self.scale_size) for frame in frames] # Resize the frame to 50% of its original size
        frame_count += 1
        view(batch_frames[0], winname='video_id')
        detections = [self.id]
        # When the batch is full or end-of-video is reached, process the batch.
        results = self.yolo_model(
            batch_frames, classes=[0], device=self.device, verbose=False
        )
        index = 0
        # annotated_frame = results[0].plot()
        # view(annotated_frame, winname='video_id')

        for result, frame in zip(results, batch_frames):
            boxes = result.boxes.xyxy.type(torch.int32)
            for box in boxes:
                x1, y1, x2, y2 = box
                if x2 - x1 < 20 or y2 - y1 < 20: continue

                detected_person_image = frame[y1:y2, x1:x2]
                faces = self.face_recognizer.recognize_faces(detected_person_image)
                for detected_face in faces:
                    if detected_face["label"] is not None:
                        detections.append((detected_face["label"], frames[index]))
                        self.logger.debug(
                            f"[{self.id}] Detected face: {detected_face['label']} with confidence {detected_face['confidence']}"
                        )
                    else:
                        detections.append((None, frames[index]))
        index += 1


        total_time = time.time() - start_time
        average_fps = frame_count / total_time if total_time > 0 else 0
        print(f"\n[{self.id}] Average FPS: {average_fps:.2f}")
        print(f"[{self.id}] Total frames: {frame_count}")
        print(f"[{self.id}] Total time: {total_time:.2f}s\n")

        return detections

def initialize_frame_controller(resources: list[Union[int, str]], *,
                                yolo_model_name: str,
                                fps= 30,
                                max_queue_size=None,
                                device='cpu',
                                timeout=0.1,
                                face_recogniser_threshold= 0.5,
                                batch_size=1,
                                scale_size=0
                        ) -> VideoFrameController:

    if max_queue_size is None:
        max_queue_size = len(resources) * fps + 1

    sources = []
    fifo_queue = Queue(maxsize=max_queue_size)
    for resource in resources:
        source = VideoProcessor(resource, device=device, yolo=yolo_model_name, face_recogniser_threshold=face_recogniser_threshold,
                                fifo_queue=fifo_queue, timeout=timeout, fps=fps, batch_size=batch_size, scale_size=scale_size)
        sources.append(source)

    frame_controller = VideoFrameController(sources, fifo_queue=fifo_queue)
    return frame_controller

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

