from abc import ABC, abstractmethod
from multiprocessing import Process


class FrameSource(ABC, Process):

    def __init__(self, id, *, stream, **kwargs):
        super().__init__(**kwargs)
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