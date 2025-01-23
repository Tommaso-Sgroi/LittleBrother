import os.path
from multiprocessing import Queue
import cv2 as cv
from camera.frame_controller import FrameController
from camera.video_source import VideoSource


def initializer(video_paths: list, timeout=0.1) -> FrameController:
    video_sources = []
    fifo_queue = Queue()

    for video_path in video_paths:
        video_id = os.path.basename(video_path)
        video_frame_source = VideoSource(video_id, video_path, fifo_queue=fifo_queue, timeout=timeout)

        video_sources.append(video_frame_source)

    frame_controller = FrameController(video_sources, fifo_queue=fifo_queue)
    return frame_controller, fifo_queue


def view(frame, *, scale=0.5, window_name='Frame'):
    """
    :param frame: frame to draw on
    :param scale: scale factor to scale the frame by
    :return: stop the drawing of the frame
    """
    # Resize frame to    a normal view
    frame = cv.resize(frame, None, fx=scale, fy=scale, interpolation=cv.INTER_LINEAR)
    cv.imshow(window_name, frame)
    key = cv.waitKey(1)
    if key in [27, ord('q'), ord('Q')]:
        return False
    return True


if __name__ == '__main__':
    videos = \
"""WiseNET/wisenet_dataset/video_sets/set_1/video1_1.avi
WiseNET/wisenet_dataset/video_sets/set_1/video1_2.avi
WiseNET/wisenet_dataset/video_sets/set_1/video1_3.avi
WiseNET/wisenet_dataset/video_sets/set_1/video1_4.avi
WiseNET/wisenet_dataset/video_sets/set_1/video1_5.avi""".split('\n')

    controller, queue = initializer(videos, timeout=0.1)
    # controller = initializer(['WiseNET/wisenet_dataset/video_sets/set_1/video1_1.avi'])

    # test video source
    # video_source: VideoSource = controller.sources[0]
    # print(video_source.stream.isOpened())
    # print(video_source.stream.read())
    # quit()
    # video_source.start()
    # while True:
    #     frames = queue.get()
    #     for frame in frames:
    #         view(frame)


    controller.start()
    from time import sleep
    while True:
        sleep(1)
        frames = controller.get_frames()
        for frame in frames:
            view(frame)

        if len(frames) == 0:
            break


