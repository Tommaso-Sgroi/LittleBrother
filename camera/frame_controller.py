import queue
from multiprocessing import Queue
from queue import Empty
from threading import Thread, Lock
from numpy import ndarray

from local_utils.logger import Logger
from .frame_source import QueuedFrameSource, FrameSource


class VideoFrameController(Thread, Logger):
    """
    Get frames from the frame sources Queue into a buffer.
    This is a thread which parses the frames from the queue into the buffer.
    usage:
    producer - consumer:
    ```
        controller = initializer(['source3', 'source2', 'source3'], timeout=-1, max_queue_size=15)
        controller.start()
    ```
    single threaded:
    ```
        controller = initializer(['source3', 'source2', 'source3'], timeout=-1, max_queue_size=15)
        while controller.has_alive_sources():
            try:
                sourceids_frames = controller.fetch_and_get_frames()
            except queue.Empty:
                # handle
            for sourceid, frames in sourceids_frames:
                pass
    ```
    """

    class Buffer:
        """Thread safe buffer list"""

        def __init__(self):
            self._buffer = []
            self.mutex_lock = Lock()

        def is_empty(self):
            with self.mutex_lock:
                return not self._buffer

        def append(self, x):
            with self.mutex_lock:
                self._buffer.append(x)

        def remove(self, x):
            with self.mutex_lock:
                self._buffer.remove(x)

        def get(self, *, flush=False):
            with self.mutex_lock:
                buffer = self._buffer
                if flush:
                    self._buffer = []
                return buffer

    def __init__(self, sources: list[FrameSource], fifo_queue: Queue):
        Logger.__init__(self, name=f"{self.__class__.__name__}")
        Thread.__init__(self)

        self.sources = sources
        self.buffer = VideoFrameController.Buffer()
        self.fifo_queue = fifo_queue

    def _alive_counter(self):
        dead_counter = 0
        for source in self.sources:
            if not source.is_alive():
                dead_counter += 1
        return len(self.sources) - dead_counter

    def has_alive_sources(self):
        return self._alive_counter() > 0

    def has_empty_buffer(self):
        return self.buffer.is_empty()

    def fetch_frames(self, timeout):
        remote_frames = self.fifo_queue.get(timeout=timeout)
        self.buffer.append(remote_frames)

    def get_frames(self) -> list[tuple[str, ndarray]]:
        """returns a list of: the frame source id (See VideoSource) and the frame np.array"""
        return [
            frame.pop()  # de-encapsulate the frames -> (frame_source_id, frame)
            for frame in self.buffer.get(flush=True)
        ]

    def fetch_and_get_frames(self, timeout=0.1) -> list[tuple[str, ndarray]]:
        """Same as calling fetch_frames() and then get_frames()"""
        try:
            self.fetch_frames(timeout)
        except queue.Empty:
            self.logger.debug(f'cannot read frames: empty queue')
        return self.get_frames()

    def run(self, *, timeout=0.1):
        self.logger.info('starting')
        self.start_frame_sources()
        while self._alive_counter() > 0:
            try:
                self.fetch_frames(timeout)
            except Empty as e:
                self.logger.debug(f'cannot read frames: empty queue')
            except Exception as e:
                self.logger.critical(f'cannot read frames: %s', e)
                return 1
        self.stop_sources()
        self.logger.info("exiting")
        return 0

    def start_frame_sources(self):
        for source in self.sources:
            source.start()

    def stop_sources(self):
        self.logger.info(f'stopping frame sources')
        for source in self.sources: source.kill()
        for source in self.sources: source.join()
        self.logger.info(f'stopped all frame sources')
