from queue import Empty
from time import sleep

from camera.video_frame_initializer import QueuedFrameControllerFactory
from people_detector.people_detector import PeopleDetector
from local_utils.view import view
from local_utils.logger import init_logger
import logging
if __name__ == '__main__':
    init_logger(logging.DEBUG)
    videos = \
        """../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_1.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_2.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_3.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_4.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_5.avi""".split('\n')

    videos = [video.strip() for video in videos] + [0]
    videos = [0]
    fps = 120

    controller = QueuedFrameControllerFactory().initializer(videos, timeout=-1, fps=60)

    yolosize = 'n'
    yolo11 = PeopleDetector(f"yolo11{yolosize}.pt", verbose=False, )
    yolo11.to('cpu')
    #
    # overlap_threshold = 0.0005
    # area_threshold = 700
    # motion_detector = MotionDetector(area_threshold=area_threshold, overlap_threshold=overlap_threshold)
    #
    # face_recognizer = FaceRecognizer(threshold=0.5)


    MULTI_THREAD = False
    DETECT_PEOPLE = False
    def plot_detected_people(sourceids_frames):
        for i in range(len(sourceids_frames)):
            video_id = sourceids_frames[i][0]
            frame = sourceids_frames[i][1]

            probs, bboxes, result = yolo11.detect(frame)
            print('confidence scores', probs)
            print('bboxes', bboxes)
            annotated_frame = result.plot()
            sourceids_frames[i] = (str(video_id), annotated_frame)

        iter_and_plot(sourceids_frames)

    def iter_and_plot(sourceids_frames):
        for id, frame in sourceids_frames:
            id = str(id)
            view(frame, winname=id)

    if MULTI_THREAD:
        controller.start()
        i = 0
        while True:
            sleep(1)
            sourceids_frames = controller.get_frames()
            if DETECT_PEOPLE:
                plot_detected_people(sourceids_frames)
            else:
                iter_and_plot(sourceids_frames)
    else:
        controller.start_frame_sources()
        while controller.has_alive_sources():
            try:
                sourceids_frames = controller.fetch_and_get_frames()
            except Empty:
                continue
            if DETECT_PEOPLE:
                plot_detected_people(sourceids_frames)
            else:
                iter_and_plot(sourceids_frames)