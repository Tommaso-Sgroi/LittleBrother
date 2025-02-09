import logging
import sys

from local_utils.config import Config


def init_logger(config: Config):
    """
    Inizializza il logger root con un handler base su console.
    Puoi arricchire questa funzione per configurazioni più complesse.
    """
    logger = logging.getLogger()
    logger.setLevel(config.logger_config['level'])

    # Se il logger root ha già degli handler, non aggiungiamo nulla.
    if not logger.handlers:
        formatter = logging.Formatter(
                fmt=config.logger_config['format'],
                datefmt=config.logger_config['datefmt']
            )
        if config.logger_config['to_file']:
            handler = logging.FileHandler(config.logger_config['file_path'])
        else:
            handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def get_logger(name: str):
    """
    Restituisce (o crea, se non esiste) un logger con il nome specificato.
    Non modifica la configurazione (handler, formatter): quella è gestita da `init_logger()`.
    """
    return logging.getLogger(name)


class Logger(object):
    def __init__(self, name):
        self.logger: logging.Logger = logging.getLogger(name)


