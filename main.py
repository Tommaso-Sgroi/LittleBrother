import sys
from threading import Thread
from time import sleep

from camera.frame_controller import VideoFrameController
from db.db_lite import TBDatabase, TDBAtomicConnection
from local_utils.config import Config, load_config
from local_utils.logger import get_logger, init_logger
from main.video_processor import initialize_frame_controller
import signal

logger = get_logger(__name__)
config: Config = load_config()

import msg_bot.telegram_bot as t_bot



def init_database(config: Config):
    db = TBDatabase(config.db_path, drop_db=config.drop_db)
    return db



def init_frame_controller(config: Config):
    frame_controller = initialize_frame_controller(**config.frame_controller_config)
    return frame_controller


def handle_signal(frame_controller:VideoFrameController):
    def signal_handler(sig, frame):
        logger.info('SIGINT received')

        logger.info(f'stopping frame sources')
        frame_controller.stop_sources()
        logger.info(f'stopped all frame sources')

        logger.info("Stopping the bot")
        t_bot.stop_bot()
        logger.info("Bot stopped")

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

def check_access(person, camera_id, database: TDBAtomicConnection):
    has_access = database.has_access_to_room(person, camera_id)
    return has_access


def main(db, frame_ctr):
    with db() as db:
        while frame_ctr.has_alive_sources():
            sleep(1)

            detections = frame_ctr.fetch_and_get_frames()  # list[Union[int, str], list[str, tuple[str, str]]]
            if len(detections) == 0:
                continue

            for camera_id, person_img in detections:
                person, img = person_img

                if check_access(person, camera_id, db):
                    continue

                logger.critical(f'Person {person} has no access to room {camera_id}')
                if person is None: person = 'Unknown'

                camera_name = db.get_camera_name(camera_id)
                t_bot.send_detection_img(img, person_detected_name=person, access_camera_name=camera_name)


if __name__ == "__main__":

    init_logger(config)

    database = init_database(config)
    frame_controller = init_frame_controller(config)


    # spawn a thread to handle signals
    frame_controller.start_frame_sources()
    telegram_bot = Thread(target=t_bot.start_bot, args=(config.logger_config['level'],), daemon=False)
    main_thread = Thread(target=main, args=(database, frame_controller), daemon=False)

    telegram_bot.start()
    sleep(1)
    main_thread.start()

    handle_signal(frame_controller)
    sys.exit(0)

