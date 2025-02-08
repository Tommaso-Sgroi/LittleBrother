from multiprocessing import Queue
from .frame_source import QueuedFrameSource


class VideoSource(QueuedFrameSource):

    def __init__(self, id, video_path: str, fifo_queue: Queue, timeout=0.1, fps=30):
        super().__init__(id, fifo_queue, timeout, fps, stream=None, daemon=False)
        self.video_path = video_path

    def queue_video_frame(self, frame):
        super().queue_video_frame(frame)



