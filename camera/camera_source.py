from multiprocessing import Queue
from typing import Union

from camera.frame_source import QueuedFrameSource


class CameraSource(QueuedFrameSource):

    def __init__(self, id, camera_name: Union[int, str], fifo_queue: Queue, timeout=0.1, fps=30):
        """
        id: The ID of the camera from which frames will be read. this will be used by opencv to read from the camera.
        """
        camera_name = str(camera_name)
        super().__init__(id, camera_name, timeout=timeout, fifo_queue=fifo_queue, fps=fps, daemon=False)


    def queue_video_frame(self, frame):
        super().queue_video_frame(frame)



