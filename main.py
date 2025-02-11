from threading import Thread
from time import sleep

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

    cameras_names = [(vfc.id, vfc.name) for vfc in config.video_frame_controller.sources]

    with db() as db_conn:
        for camera_id, camera_name in cameras_names:
            db_conn.add_camera(camera_id, camera_name)
    return db


def init_frame_controller(config: Config):
    # conf = config.video_frame_controller.sources.copy()
    # # remove all second elements of the tuple
    frame_controller = initialize_frame_controller(config.video_frame_controller)
    return frame_controller


def check_access(person, camera_id, database: TDBAtomicConnection):
    has_access = database.has_access_to_room(person, camera_id)
    return has_access


def handle_signal(sig, frame, frame_controller):
    logger.info("SIGINT received, shutting down services.")
    t_bot.stop_bot()
    frame_controller.stop_sources()
    exit(0)

def register_signal_handler(frame_controller):
    signal.signal(signal.SIGINT, lambda s, f: handle_signal(s, f, frame_controller))

def process_detections(database, frame_controller):
    """Process detections continuously."""
    frame_controller.start_frame_sources()
    while not frame_controller.sources_setup_complete():
        logger.info("Waiting for frame sources to be setup")
        sleep(0.5)
    with database() as db:
        while frame_controller.has_alive_sources():
            detections = frame_controller.fetch_and_get_frames()
            if not detections:
                continue
            for detection in detections:
                for camera_id, person, img in detection:
                    if check_access(person, camera_id, db):
                        continue
                    logger.critical(f"Person {person or 'Unknown'} has no access to room {camera_id}")
                    camera_name = db.get_camera_name(camera_id)
                    t_bot.send_detection_img(img, person_detected_name=person or "Unknown", access_camera_name=camera_name)
    frame_controller.stop_sources()

def run_app():
    init_logger(config)
    database = init_database(config)
    frame_controller = init_frame_controller(config)
    register_signal_handler(frame_controller)
    
    bot_thread = Thread(target=t_bot.start_bot, args=(config.logger_config['level'], True), daemon=False)
    detections_thread = Thread(target=process_detections, args=(database, frame_controller), daemon=False)
    
    bot_thread.start()
    sleep(5)
    detections_thread.start()
    bot_thread.join()
    detections_thread.join()

if __name__ == "__main__":
    run_app()


