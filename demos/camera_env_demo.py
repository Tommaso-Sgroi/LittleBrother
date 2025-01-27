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

    controller = initializer(videos, timeout=-1, max_queue_size=100)

    yolosize = 'n'
    yolo11 = PeopleDetector(f"yolo11{yolosize}.pt", verbose=False, )
    yolo11.to('cpu')

    overlap_threshold = 0.0005
    area_threshold = 700
    motion_detector = MotionDetector(area_threshold=area_threshold, overlap_threshold=overlap_threshold)

    face_recognizer = FaceRecognizer(threshold=0.5)
    # face_5 = Image.open('demo_images/face_5.jpg')
    # face_recognizer.enroll_face(face_5, 'Michael Scott', overwrite=True)

    # probs, bboxes, result = yolo11.detect(frame)
    # print('confidence scores', probs)
    # print('bboxes', bboxes)
    # annotated_frame = result.plot()

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


    i = 0
    while True:
        sleep(1)
        frames = controller.get_frames()
        for video_id, frame in frames:
            probs, bboxes, result = yolo11.detect(frame)
            print('confidence scores', probs)
            print('bboxes', bboxes)
            annotated_frame = result.plot()
            view(annotated_frame, winname=video_id)

        if len(frames) == 0:
            break
