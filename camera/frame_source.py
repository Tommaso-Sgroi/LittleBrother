
from local_utils.logger import Logger
from abc import ABC, abstractmethod
from multiprocessing import Process


class FrameSource(ABC, Process, Logger):

    def __init__(self, id, *, stream, **kwargs):
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