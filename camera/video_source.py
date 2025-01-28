import queue

from .frame_source import FrameSource
import cv2 as cv
from multiprocessing import Queue
from .utils import rate_limit
from time import sleep
class VideoSource(FrameSource):

    def __init__(self, id, video_path: str, fifo_queue: Queue, timeout=0.1):
        self.video_path = video_path
        # video_capture = cv.VideoCapture(video_path)
        self.queue = fifo_queue
        self.timeout = timeout
        self.wait_backoff = 1
        super().__init__(id, stream=None, daemon=False)

    @rate_limit(15)
    def read(self):
        return self.stream.read()

    def next(self):
        ret, frame = self.read()
        if not ret:
            raise StopIteration()
        return frame

    def _increase_backoff(self):
        self.wait_backoff *= 1.5

    def _decrease_backoff(self):
        self.wait_backoff /= 1.2

    def _calculate_backoff_time(self):
        return self.wait_backoff * (10 ** -1)

    def run(self):
        # lo stream va inserito per forza qua altrimenti non funziona nulla
        self.logger.info('starting video')
        self.stream = cv.VideoCapture(self.video_path)

        if not self.stream.isOpened():
            self.logger.critical(f'stream {self.video_path} not opened')
            return 1

        try:
            while True:
                frame = self.next()
                while True:
                    self.logger.debug('backoff timer %s', str(self.wait_backoff))
                    try:
                        # wait backoff time
                        sleep(self._calculate_backoff_time())
                        # send messages
                        self.queue.put([(self.id, frame)], timeout=self.timeout)
                        self._decrease_backoff()
                        break
                    except queue.Full as qf:
                        self.logger.debug(f'cannot send video frame: queue full')
                        self._increase_backoff()
                    except Exception as ex:
                        self.logger.critical(f'cannot send video frame: %s', ex)
                        return 1
        except StopIteration:
            self.logger.info(f'no more frames, exiting')
            return 0
