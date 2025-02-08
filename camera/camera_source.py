from multiprocessing import Queue

from camera.frame_source import QueuedFrameSource


class CameraSource(QueuedFrameSource):

    def __init__(self, id, camera_id: int, fifo_queue: Queue, timeout=0.1, fps=30):
        super().__init__(id, fifo_queue, timeout, fps, stream=None, daemon=False)
        self.camera_id = camera_id

    def queue_video_frame(self, frame):
        super().queue_video_frame(frame)



