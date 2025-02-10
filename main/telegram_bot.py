import msg_bot.telegram_bot as t_bot
from multiprocessing import Process, Queue
from queue import Empty
from local_utils.logger import Logger


class TelegramBotProcess(Process, Logger):
    def __init__(self, config, notifications_queue: Queue, **kwargs):
        """
        A Process that starts the Telegram bot in a separate thread and
        consumes images from 'notifications_queue' to send them via the bot.

        Args:
            config: A configuration object that includes 'logger_config' etc.
            notifications_queue (Queue): A queue from which we pull (img, person, camera_name).
            kwargs: Additional arguments passed to `multiprocessing.Process`.
        """
        Process.__init__(self, **kwargs)
        Logger.__init__(self, name=self.__class__.__name__)
        self.config = config
        self.notifications_queue = notifications_queue
        self.bot_thread = None

    def start_bot(self):
        """
        Create and start the Telegram bot thread, using the config's logger level
        and the notifications queue.
        """
        self.bot_thread = t_bot.TelegramBotThread(
            target=t_bot.start_bot,
            args=(self.config.logger_config["level"], self.notifications_queue),
            daemon=True
        )
        self.bot_thread.start()

    def terminate(self):
        """
        Stop the bot by calling 't_bot.stop_bot()', if implemented to end the polling.
        """
        self.bot_thread.stop()
        self.bot_thread.join()
        super().terminate()

    def send_images(self):
        """
        Continuously fetches (img, person, camera_name) from the notifications queue
        and calls 't_bot.send_detection_img(...)' to send them via Telegram.
        Stops when the bot thread is no longer alive.
        """
        while self.bot_thread.is_alive():
            try:
                img, person, camera_name = self.notifications_queue.get(timeout=1)
                t_bot.send_detection_img(
                    img,
                    person_detected_name=person,
                    access_camera_name=camera_name
                )
            except Empty:
                self.logger.debug("Notifications queue is empty")
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")

    def run(self):
        """
        Entry point of the Process. Starts the bot in a thread, then
        loops to send images from the queue until the bot thread is dead.
        """
        self.start_bot()
        self.send_images()
        # Once the bot thread ends, we exit run().
        return 0
