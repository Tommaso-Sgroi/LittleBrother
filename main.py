from multiprocessing import Queue
from threading import Thread

from db.db_lite import TBDatabase
from local_utils.config import Config, load_config
from local_utils.logger import get_logger
from time import sleep
from main.video_processor import initialize_frame_controller
from main.telegram_bot import TelegramBotProcess
import signal
import sys

logger = get_logger(__name__)


def init_database(config: Config):
    db = TBDatabase(config.db_path, drop_db=config.drop_db)  # todo change me
    return db


def init_telegram_bot(queue, config: Config):
    telegram_bot_process = TelegramBotProcess(config=config, img_queue=queue)
    return telegram_bot_process


def init_frame_controller(config: Config):
    frame_controller = initialize_frame_controller(**config.frame_controller_config)
    return frame_controller


def handle_signal(processes):
    def signal_handler(sig, frame):
        logger.info('SIGINT received')
        for p in processes: p.stop()
        for p in processes: p.join()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGKILL, signal_handler)
    signal.pause()

def main(database):
    while True:
        sleep(1)
        detections = frame_controller.get_frames()  # list[Union[int, str], list[str, tuple[str, str]]]
        if len(detections) == 0:
            continue
        for camera_id, person_img in detections:
            person, img = person_img
            has_access = database.has_access_to_room(person, camera_id)
            if has_access:
                continue

            logger.critical(f'Person {person} has no access to room {camera_id}')
            if person is None: person = 'Unknown'

            camera_name = database.get_camera_name(camera_id)
            message_queue.put((camera_name, person, img))


if __name__ == "__main__":

    config: Config = load_config()

    message_queue = Queue()

    database = init_database(config)
    frame_controller = init_frame_controller(config)
    telegram_bot = init_telegram_bot(message_queue, config)

    processes = [frame_controller, telegram_bot]
    # spawn a thread to handle signals
    signal_handler = Thread(target=handle_signal, args=(processes.copy(),), daemon=True)

    processes.append(signal_handler)
    for p in processes:
        p.start()

    with database() as database:
        main(database)


    for p in processes:
        p.join()

    # frame_controller.start()
    # frame_controller.stop_sources()
    #
    # while True:
    #     sleep(1)
    #     sourceids_frames = frame_controller.get_frames()
    #     # [frame_source_id, ('label', frame)]
    #     if len(sourceids_frames) > 0:
    #         pass
    #     print('Aiuto')
    #     for label, frame in sourceids_frames:
    #         print(label, frame)
    #         view(frame, winname=label)
