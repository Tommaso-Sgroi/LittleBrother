import logging
import sys

def init_logger(level=logging.INFO):
    """
    Inizializza il logger root con un handler base su console.
    Puoi arricchire questa funzione per configurazioni più complesse.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Se il logger root ha già degli handler, non aggiungiamo nulla.
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

def get_logger(name: str):
    """
    Restituisce (o crea, se non esiste) un logger con il nome specificato.
    Non modifica la configurazione (handler, formatter): quella è gestita da `init_logger()`.
    """
    return logging.getLogger(name)


class Logger(object):
    def __init__(self, name):
        self.logger: logging.Logger = logging.getLogger(name)

if __name__ == '__main__':
    init_logger(level=logging.DEBUG)
    logging.getLogger('hello').info('Hello World!')
    logging.getLogger('hello').debug('Hello World!')
    logging.getLogger('Heyy').error('ao pupa')
    try:
        raise Exception('thorny problem')
    except Exception as e:
        logging.getLogger('Heyy').debug("Houston, we have a %s", e, exc_info=False)
        logging.getLogger('Heyy').debug("Houston, we have a second %s", e)
        logging.getLogger('Heyy').debug("Houston, we have a third %s", e, exc_info=True)
