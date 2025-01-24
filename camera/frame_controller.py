from multiprocessing import Queue
from queue import Empty
from threading import Thread, Lock
from numpy import ndarray

from .frame_source import FrameSource


class FrameController(Thread):
    """
    Get frames from the frame sources Queue into a buffer.
    This is a thread which parses the frames from the queue into the buffer.
    """
    class Buffer:
        """Thread safe buffer list"""
        def __init__(self):
            self._buffer = []
            self.mutex_lock = Lock()

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
        super().__init__()
        self.sources = sources
        self.buffer = FrameController.Buffer()
        self.fifo_queue = fifo_queue

    def _alive_counter(self):
        dead_counter = 0
        for source in self.sources:
            if not source.is_alive():
                dead_counter += 1
        return len(self.sources) - dead_counter

    def fetch_frames(self, timeout=0.1):

        while self._alive_counter() > 0:
            try:
                remote_frames = self.fifo_queue.get(timeout=timeout)
                self.buffer.append(remote_frames)
            except Empty as e:
                print(f'Frame controller: queue is empty')
        return 1

    def get_frames(self) -> list[tuple[str, ndarray]]:
        """returns a list of: the frame source id (See VideoSource) and the frame np.array"""
        return [
            frame.pop() # de-encapsulate the frames -> (frame_source_id, frame)
            for frame in self.buffer.get(flush=True)
        ]

    def run(self, *, timeout=0.1):
        for source in self.sources:
            source.start()
        return self.fetch_frames(timeout)

    def stop(self):
        for source in self.sources: source.kill()
        for source in self.sources: source.join()
