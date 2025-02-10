import functools
import time


# rate limit to n fps
def rate_limit(method):
    """
    Decoratore che limita la frequenza di chiamata di 'method'
    in base a 'self.fps', salvando l'ultimo timestamp in 'self._last_call'.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        # Se l'istanza non ha _last_call, lo inizializziamo a 0
        if not hasattr(self, '_last_call'):
            self._last_call = 0

        # Se non esiste 'self.fps', usiamo un default (ad es. 30)
        fps = getattr(self, 'fps', 30)
        if fps <= 0:
            # Se per qualche ragione fps è 0 o negativo, nessun rate limit
            return method(self, *args, **kwargs)

        min_interval = 1.0 / fps
        now = time.time()
        elapsed = now - self._last_call

        # Se abbiamo chiamato il metodo troppo di recente, aspettiamo
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

        result = method(self, *args, **kwargs)
        self._last_call = time.time()
        return result

    return wrapper

