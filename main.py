import sys
from multiprocessing import Process, Queue
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


def handle_signal(processes):
    def signal_handler(sig, frame):
        logger.info("SIGINT received")

        logger.info("Stopping the bot")
        t_bot.stop_bot()
        logger.info("Bot stopped")

        # Terminate all processes
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()


def check_access(person, camera_id, database: TDBAtomicConnection):
    has_access = database.has_access_to_room(person, camera_id)
    return has_access


def main_process(config, notifications_queue: Queue):
    # Initialize resources locally in the process
    database = init_database(config)
    frame_controller = init_frame_controller(config)
    frame_controller.start_frame_sources()

    with database() as db:
        while frame_controller.has_alive_sources():
            sleep(1)

            detections = frame_controller.fetch_and_get_frames()
            if len(detections) == 0:
                continue

            for camera_id, person_img in detections:
                person, img = person_img

                if check_access(person, camera_id, db):
                    continue

                logger.critical(f"Person {person} has no access to room {camera_id}")
                if person is None:
                    person = "Unknown"

                camera_name = db.get_camera_name(camera_id)
                # Send notification through queue instead of direct bot call
                notifications_queue.put((img, person, camera_name))

    frame_controller.stop_sources()


if __name__ == "__main__":

    init_logger(config)

    # Create notifications queue
    notifications_queue = Queue()

    # spawn processes
    telegram_bot = Process(
        target=t_bot.start_bot,
        args=(config.logger_config["level"], notifications_queue),
        daemon=False,
    )
    main_proc = Process(
        target=main_process, args=(config, notifications_queue), daemon=False
    )

    processes = [telegram_bot, main_proc]

    telegram_bot.start()
    sleep(1)
    main_proc.start()

    handle_signal(processes)
    sys.exit(0)
