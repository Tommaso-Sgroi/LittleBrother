import os.path
from multiprocessing import Queue
from .frame_controller import VideoFrameController
from .video_source import VideoSource


def initializer(video_paths: list, max_queue_size = 1024, timeout=0.1) -> VideoFrameController:
    video_sources = []
    fifo_queue = Queue(maxsize=max_queue_size)

    for video_path in video_paths:
        video_id = os.path.basename(video_path)
        video_frame_source = VideoSource(video_id, video_path, fifo_queue=fifo_queue, timeout=timeout)

        video_sources.append(video_frame_source)

    frame_controller = VideoFrameController(video_sources, fifo_queue=fifo_queue)
    return frame_controller
