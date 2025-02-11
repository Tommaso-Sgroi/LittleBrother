from abc import ABC, abstractmethod
from multiprocessing import Queue
from local_utils.config import VideoFrameControllerConfig, QueuedFrameSourceConfig, FrameSourceConfig
from .frame_controller import VideoFrameController
from .frame_source import FrameSource, QueuedFrameSource


class AbstractFrameControllerFactory(ABC):


    @abstractmethod
    def build_source(self, source: FrameSourceConfig, **kwargs) -> FrameSource:
        pass

    @abstractmethod
    def initializer(self, config:VideoFrameControllerConfig) -> VideoFrameController:
        pass

    def _instantiate_source(self, sources: list[FrameSourceConfig], **kwargs) -> list[FrameSource]:
        sources_built = []
        for source in sources:
            source = self.build_source(source, **kwargs)
            sources_built.append(source)
        return sources_built

class QueuedFrameControllerFactory(AbstractFrameControllerFactory):

    def initializer(self, config: VideoFrameControllerConfig) -> VideoFrameController:
        """
        Initialize a VideoFrameController with the given configuration.
        """
        max_queue_size = config.max_queue_size
        if config.max_queue_size is None:
            mean_fps = sum([x.fps for x in config.sources]) // len(config.sources)
            max_queue_size = mean_fps + 1

        fifo_queue = Queue(maxsize=max_queue_size)

        frame_sources = self._instantiate_source(config.sources, fifo_queue=fifo_queue)

        frame_controller = VideoFrameController(frame_sources, fifo_queue=fifo_queue)
        return frame_controller


    def build_source(self, source: QueuedFrameSourceConfig, **kwargs) -> FrameSource:
        return QueuedFrameSource(source.to_dict(), **kwargs)
