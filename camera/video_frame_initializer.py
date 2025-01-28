import os.path
from multiprocessing import Queue
from .frame_controller import VideoFrameController
from .video_source import VideoSource


def initializer(video_paths: list, *, max_queue_size=None, timeout=0.1, fps=15) -> VideoFrameController:
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
        video_id = os.path.basename(video_path)
        video_frame_source = VideoSource(video_id, video_path, fifo_queue=fifo_queue, timeout=timeout, fps=fps)

        video_sources.append(video_frame_source)

    frame_controller = VideoFrameController(video_sources, fifo_queue=fifo_queue)
    return frame_controller
