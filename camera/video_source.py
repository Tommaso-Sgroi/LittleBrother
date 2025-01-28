import queue
import time
import functools
import cv2 as cv
from multiprocessing import Queue
from .frame_source import FrameSource


def rate_limit(method):
    """
    Decoratore che limita la frequenza di chiamata di 'method'
    in base a 'self.fps', salvando l'ultimo timestamp in 'self._last_call'.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # Se l'istanza non ha _last_call, lo inizializziamo a 0
        if not hasattr(self, '_last_call'):
            self._last_call = 0

        # Se non esiste 'self.fps', usiamo un default (ad es. 30)
        fps = getattr(self, 'fps', 30)
        if fps <= 0:
            # Se per qualche ragione fps è 0 o negativo, nessun rate limit
            return method(self, *args, **kwargs)

        min_interval = 1.0 / fps
        now = time.time()
        elapsed = now - self._last_call

        # Se abbiamo chiamato il metodo troppo di recente, aspettiamo
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        result = method(self, *args, **kwargs)
        self._last_call = time.time()
        return result

    return wrapper


class VideoSource(FrameSource):
    def __init__(self, id, video_path: str, fifo_queue: Queue, timeout=0.1, fps=30):
        super().__init__(id, stream=None, daemon=False)

        self.video_path = video_path
        self.queue = fifo_queue
        self.timeout = timeout
        self.fps = fps

    @rate_limit
    def read(self):
        """
        Legge un frame dal video. L'accesso è rate-limitato dal decoratore.
        """
        return self.stream.read()

    def next(self):
        ret, frame = self.read()
        if not ret:
            raise StopIteration()
        return frame


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
                try:
                    self.queue.put([(self.id, frame)], timeout=self.timeout)
                except queue.Full:
                    self.logger.debug(f'cannot send video frame: queue full, skipping frame')
                except Exception as ex:
                    self.logger.critical(f'cannot send video frame: %s', ex)
                    return 1
        except StopIteration:
            self.logger.info(f'no more frames, exiting')
            return 0
