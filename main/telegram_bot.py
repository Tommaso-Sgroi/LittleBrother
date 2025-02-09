from multiprocessing import Process, Queue
from threading import Thread
from typing import Union

from local_utils.config import Config, config
from local_utils.logger import Logger
from PIL import Image

class TelegramBotProcess(Process, Logger):

    def __init__(self, config: Config, img_queue: Queue, **kwargs):
        Logger.__init__(self, __name__)
        Process.__init__(self, **kwargs)
        self.config = config
        self.img_queue = img_queue
        self.bot = None


    def stop(self):
        self.bot.stop_bot()
        self.terminate()
    
    def run(self):
        import msg_bot.telegram_bot as t_bot

        Thread(target=run_img_sender, args=(self.logger, self.img_queue, t_bot.send_detection_img), daemon=True).start()

        t_bot.start_bot(config.logger_config['level'])
        self.bot = t_bot.bot

        return 0


def run_img_sender(logger, queue: Queue, send_detection_img):

    while True:
        try:
            img = queue.get()
            for camera_name, label, img in img:
                send_detection_img(img, person_detected_name=label, access_camera_name=camera_name)
        except Exception as e:
            logger.fatal(f'error in telegram bot: {e}')
            break
    logger.info('exiting')
