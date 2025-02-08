import os.path
from multiprocessing import Queue
from typing import Union

from .camera_source import CameraSource
from .frame_controller import VideoFrameController
from .frame_source import FrameSource
from .video_source import VideoSource


def initializer(video_paths: list[Union[str,int]], *, max_queue_size=None, timeout=0.1, fps=15) -> VideoFrameController:
    """
    Creates and configures a video frame controller along with its associated video sources.

    This function:
      1. Optionally calculates a maximum queue size based on the number of video paths and FPS.
      2. Initializes a multiprocessing-safe queue to buffer frames from multiple video sources.
      3. Creates a `VideoSource` instance for each video path, assigning each a unique ID based on the file name.
      4. Wraps all created sources in a `VideoFrameController`, which coordinates the fetching and handling of frames.

    Args:
        video_paths (list):
            A list of file paths to the videos that will be processed.
        max_queue_size (int, optional):
            The maximum number of items the frame queue can hold.
            If not provided, a default is computed as `len(video_paths) * fps + 1`.
        timeout (float, optional):
            The timeout (in seconds) for queue operations when putting frames. Defaults to 0.1.
        fps (int, optional):
            The desired frames per second for reading from each video source. Defaults to 15.

    Returns:
        VideoFrameController:
            A controller object that manages all `VideoSource` instances and coordinates frame retrieval.
    """
    video_sources = []
    if max_queue_size is None:
        max_queue_size = len(video_paths) * fps + 1

    fifo_queue = Queue(maxsize=max_queue_size)
    for video_path in video_paths:
        if type(video_path) is int:
            camera_id = f"camera{video_path}"
            source = CameraSource(camera_id, video_path, fifo_queue=fifo_queue, timeout=timeout, fps=fps)
        elif type(video_path) is str:
            video_id = os.path.basename(video_path)
            source = VideoSource(video_id, video_path, fifo_queue=fifo_queue, timeout=timeout, fps=fps)
        else:
            raise ValueError(f"Invalid video path: {video_path}")

        video_sources.append(source)

    frame_controller = VideoFrameController(video_sources, fifo_queue=fifo_queue)
    return frame_controller
