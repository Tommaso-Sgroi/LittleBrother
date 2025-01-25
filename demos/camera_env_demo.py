from camera.video_frame_initializer import initializer
from utils.view import view

if __name__ == '__main__':

    videos = \
        """../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_1.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_2.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_3.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_4.avi
        ../datasets/WiseNET/wisenet_dataset/video_sets/set_1/video1_5.avi""".split('\n')

    videos = [video.strip() for video in videos]

    controller = initializer(videos, timeout=0.1, max_queue_size=100)
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
            view(frame, winname=video_id)

        if len(frames) == 0:
            break
