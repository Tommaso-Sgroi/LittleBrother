import os.path
from multiprocessing import Queue
import cv2 as cv
from .frame_controller import FrameController
from .video_source import VideoSource


def initializer(video_paths: list, max_queue_size = 1024, timeout=0.1) -> FrameController:
    video_sources = []
    fifo_queue = Queue(maxsize=max_queue_size)

    for video_path in video_paths:
        video_id = os.path.basename(video_path)
        video_frame_source = VideoSource(video_id, video_path, fifo_queue=fifo_queue, timeout=timeout)

        video_sources.append(video_frame_source)

    frame_controller = FrameController(video_sources, fifo_queue=fifo_queue)
    return frame_controller


def view(frame, *, scale=0.5, window_name='Frame'):
    """
    :param frame: frame to draw on
    :param scale: scale factor to scale the frame by
    :return: stop the drawing of the frame
    """
    # Resize frame to    a normal view
    frame = cv.resize(frame, None, fx=scale, fy=scale, interpolation=cv.INTER_LINEAR)
    cv.imshow(window_name, frame)
    key = cv.waitKey(1)
    if key in [27, ord('q'), ord('Q')]:
        return False
    return True
