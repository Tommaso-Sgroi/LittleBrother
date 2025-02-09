from multiprocessing import Queue
from .frame_source import QueuedFrameSource


class VideoSource(QueuedFrameSource):

    def __init__(self, id, video_name: str, fifo_queue: Queue, timeout=0.1, fps=30):
        super().__init__(id, video_name, timeout=timeout, fifo_queue=fifo_queue, fps=fps, daemon=False)

    def queue_video_frame(self, frame):
        super().queue_video_frame(frame)



