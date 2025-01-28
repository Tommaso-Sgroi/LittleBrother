from camera.video_frame_initializer import initializer
from face_recognizer.face_recognizer import FaceRecognizer
from motion_detector.motion_detector import MotionDetector
from people_detector.people_detector import PeopleDetector
from utils.view import view
from utils.logger import init_logger
import logging
if __name__ == '__main__':
    init_logger(logging.DEBUG)
    videos = \
        """../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_1.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_2.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_3.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_4.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_5.avi""".split('\n')

    videos = [video.strip() for video in videos]

    controller = initializer(videos, timeout=1, max_queue_size=25)

    controller.start()
    from time import sleep


    i = 0
    sleep(1)
    numf = {}
    while True:
        frames = controller.get_frames()
        for video_id, frame in frames:
            view(frame, winname=video_id)
            if video_id in numf:
                numf[video_id] = numf[video_id] + 1
            else:
                numf[video_id] = 1
            print(numf[video_id])

        if len(frames) == 0:
            break
