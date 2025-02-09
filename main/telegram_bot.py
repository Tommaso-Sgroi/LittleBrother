from multiprocessing import Process, Queue
from typing import Union

from local_utils.config import Config
from local_utils.logger import Logger
from PIL import Image

class TelegramBotProcess(Process, Logger):

    def __init__(self, config: Config, img_queue: Queue, **kwargs):
        Logger.__init__(self, __name__)
        Process.__init__(self, **kwargs)
        self.config = config
        self.img_queue = img_queue
        self.bot = None

    def get_images_labels(self) -> list[tuple[str, Union[int, str], Image]]:
        """returns a list of: the frame source id (See VideoSource), detected face's label/name and the frame PIL image"""
        return [
            frame.pop()  # de-encapsulate the frames -> (camera_name, person_name, frame)
            for frame in self.img_queue.get()
        ]

    def stop(self):
        self.bot.stop_bot()
        self.terminate()

    def run(self):
        import msg_bot.telegram_bot as t_bot
        t_bot.start_bot(None) # todo change me
        self.bot = t_bot.bot

        while True:
            try:
                img = self.get_images_labels()
                for camera_name, label, img in img:
                    t_bot.send_detection_img(img, person_detected_name=label, access_camera_name=camera_name)
            except Exception as e:
                self.logger.fatal(f'error in telegram bot: {e}')
                break
        self.logger.info('exiting')
        self.stop()
        return 0



