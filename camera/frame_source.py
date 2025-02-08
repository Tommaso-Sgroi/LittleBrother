import queue
from camera.utils import rate_limit
from local_utils.logger import Logger
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
import cv2 as cv

class FrameSource(ABC, Process, Logger):

    def __init__(self, id, *, stream: cv.VideoCapture, **kwargs):
        Process.__init__(self, **kwargs)
        Logger.__init__(self, name=f"{self.__class__.__name__}-{id}")

        self.id = id
        self.stream = stream
        self.buffer = []


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
    def __init__(self, id, fifo_queue: Queue, timeout:float, fps:int, *, stream, **kwargs):
        FrameSource.__init__(self, id, stream=stream, **kwargs)
        self.queue = fifo_queue
        self.timeout = timeout
        self.fps = fps

    @rate_limit
    def read(self):
        """
        Legge un frame dal video. L'accesso è rate-limitato dal decoratore.
        """
        return self.stream.read()

    @abstractmethod
    def queue_video_frame(self, frame):
        self.queue.put([(self.id, frame)], timeout=self.timeout)


    def next(self):
        ret, frame = self.read()
        if not ret:
            raise StopIteration()
        return frame

    def run(self):
        try:
            self.create_stream()
            if not self.stream.isOpened():
                self.logger.error(f'cannot open stream {self.id}')
                return 1

            while True:
                frame = self.next()
                try:
                    self.queue_video_frame(frame)
                except queue.Full:
                    self.logger.debug(f'cannot send video frame: queue full, skipping frame')
                except Exception as ex:
                    self.logger.critical(f'cannot send video frame: %s', ex)
                    return 1
        except StopIteration:
            self.logger.info(f'no more frames, exiting')
            return 0
        finally:
            self.stream.release()

    def create_stream(self):
        self.stream = cv.VideoCapture(self.id)
