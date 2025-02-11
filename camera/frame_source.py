import queue
from camera.utils import rate_limit
from local_utils.logger import Logger
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
import cv2 as cv

class FrameSource(ABC, Process, Logger):
    """
    Abstract class for a frame source.
    The stream must implement the "read" and "isOpened" method
    """

    def __init__(self, id, source, **kwargs):
        Process.__init__(self, **kwargs)
        Logger.__init__(self, name=f"{self.__class__.__name__}-{id}")
        self.source = source
        self.id = id
        self.buffer = []
        self.stream = None


    @abstractmethod
    def read(self):
        """Get the next frame from the buffer
        """
        pass

    @abstractmethod
    def next(self):
        """Get the next frame from the source
        """
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def create_stream(self):
        pass

class QueuedFrameSource(FrameSource, ABC):
    def __init__(self, id, source, fifo_queue: Queue, timeout:float, fps:int, **kwargs):
        FrameSource.__init__(self, id, source,  **kwargs)
        self.queue = fifo_queue
        self.timeout = timeout
        self.fps = fps

    @rate_limit
    def read(self):
        """
        Calls stream.read(), it is rate limited by the decorator to self.fps.
        """
        return self.stream.read()

    @abstractmethod
    def queue_video_frame(self, frame):
        self.queue.put([(self.id, frame)], timeout=self.timeout)

    def create_stream(self):
        self.stream = cv.VideoCapture(self.source)

    def next(self):
        ret, frame = self.read()
        if not ret:
            raise StopIteration()
        return frame

    def run(self):
        try:
            self.create_stream()
            if not self.stream.isOpened():
                self.logger.error('[%s]cannot open stream', self.id)
                return 1

            self.logger.info("[%s] i'm up and running, starting to send frames", self.id)

            while True:
                frame = self.next()
                try:
                    self.queue_video_frame(frame)
                except queue.Full:
                    self.logger.debug('[%s] cannot send video frame: queue full, skipping frame', self.id)
                except Exception as ex:
                    self.logger.critical('[%s] cannot send video frame: %s', self.id, ex)
                    return 1
        except StopIteration:
            self.logger.info('[%s] no more frames, exiting', self.id)
            return 0
        finally:
            self.stream.release()


