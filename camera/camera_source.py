from multiprocessing import Queue

from camera.frame_source import QueuedFrameSource
from cv2 import VideoCapture

class CameraSource(QueuedFrameSource):

    def __init__(self, id, fifo_queue: Queue, timeout=0.1, fps=30):
        """
        id: The ID of the camera from which frames will be read. this will be used by opencv to read from the camera.
        """
        super().__init__(id, timeout=timeout, fifo_queue=fifo_queue, fps=fps, daemon=False)


    def queue_video_frame(self, frame):
        super().queue_video_frame(frame)


class FakeCameraSource(CameraSource):
    """
    Fakes a camera source by reading from a video file.
    """

    def __init__(self, id, fifo_queue: Queue, *, video_path,  timeout=0.1, fps=30):
        """
        id: The ID of the camera which will appear/or appear into the database.
        video_path: The path to the video file to read frames from.
        """
        super().__init__(id, timeout=timeout, fifo_queue=fifo_queue, fps=fps)
        self.video_path = video_path

    def create_stream(self):
        self.stream = VideoCapture(self.video_path)
