import queue

from .frame_source import FrameSource
import cv2 as cv
from multiprocessing import Queue
from .utils import rate_limit

class VideoSource(FrameSource):

    def __init__(self, id, video_path: str, fifo_queue: Queue, timeout=0.1):
        self.video_path = video_path
        # video_capture = cv.VideoCapture(video_path)
        self.queue = fifo_queue
        self.timeout = timeout
        super().__init__(id, stream=None, daemon=False)

    @rate_limit(30)
    def read(self):
        return self.stream.read()

    def next(self):
        ret, frame = self.read()
        if not ret:
            raise StopIteration()
        return frame


    def run(self):
        # lo stream va inserito per forza qua altrimenti non funziona nulla
        self.stream = cv.VideoCapture(self.video_path)
        try:
            while True:
                frame = self.next()
                try:
                    self.queue.put([(self.id, frame)], timeout=self.timeout)
                except queue.Full:
                    print(f'Video Source #{self.id}:Queue full')

        except StopIteration:
            print(f'stopped id {self.id}, {self.video_path}')
            return 0
