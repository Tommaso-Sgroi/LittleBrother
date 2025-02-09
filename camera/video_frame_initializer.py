import os.path
from abc import ABC, abstractmethod
from multiprocessing import Queue
from typing import Union, Any

from .camera_source import CameraSource
from .frame_controller import VideoFrameController
from .frame_source import QueuedFrameSource, FrameSource
from .video_source import VideoSource


class AbstractFrameControllerFactory(ABC):


    @abstractmethod
    def build_source(self, source: Union[Any], **kwargs) -> FrameSource:
        pass

    @abstractmethod
    def initializer(self, sources_path: list[Union[str,int]], max_queue_size=None, fps=15, **kwargs) -> VideoFrameController:
        pass

    def _instantiate_source(self, sources, **kwargs) -> list[FrameSource]:
        sources_built = []
        for source in sources:
            source = self.build_source(source, **kwargs)
            sources_built.append(source)
        return sources_built

class QueuedFrameControllerFactory(AbstractFrameControllerFactory):

    def initializer(self, sources_path: list[Union[str,int]], max_queue_size=None, fps=15, **kwargs) -> VideoFrameController:
        """
        Creates and configures a video frame controller along with its associated video sources.

        This function:
          1. Optionally calculates a maximum queue size based on the number of video paths and FPS.
          2. Initializes a multiprocessing-safe queue to buffer frames from multiple video sources.
          3. Creates a `VideoSource` instance for each video path, assigning each a unique ID based on the file name.
          4. Wraps all created sources in a `VideoFrameController`, which coordinates the fetching and handling of frames.

        Args:
            sources_path (list):
                A list of file paths to the videos that will be processed.
            max_queue_size (int, optional):
                The maximum number of items the frame queue can hold.
                If not provided, a default is computed as `len(video_paths) * fps + 1`.
            timeout (float, optional):
                The timeout (in seconds) for queue operations when putting frames. Defaults to 0.1.
            fps (int, optional):
                The desired frames per second for reading from each video source. Defaults to 15.

        Returns:
            VideoFrameController:
                A controller object that manages all `VideoSource` instances and coordinates frame retrieval.
        """
        if max_queue_size is None:
            max_queue_size = len(sources_path) * fps + 1

        fifo_queue = Queue(maxsize=max_queue_size)
        frame_sources = self._instantiate_source(sources_path, fps=fps, fifo_queue=fifo_queue, **kwargs)

        frame_controller = VideoFrameController(frame_sources, fifo_queue=fifo_queue)
        return frame_controller


    def build_source(self, source: Union[str, int], **kwargs) -> FrameSource:
        if isinstance(source, int):
            return CameraSource(id=source, camera_name=source, **kwargs)
        elif os.path.isfile(source):
            return VideoSource(id=source, video_name=os.path.basename(source), **kwargs)
        else:
            raise ValueError(f"Invalid source path: {source}")