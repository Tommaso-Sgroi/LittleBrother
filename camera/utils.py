import functools
import time


# rate limit to n fps
def rate_limit(fps=10):
    """
    Decoratore che limita la frequenza delle chiamate
    a una funzione, ad esempio read() in questo caso,
    a 'fps' frame al secondo.
    """
    def decorator(func):
        last_call = 0
        min_interval = 1.0 / fps  # intervallo minimo fra chiamate

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if min_interval > 0:
                nonlocal last_call
                now = time.time()
                elapsed = now - last_call

                # Se l'ultima chiamata è avvenuta troppo di recente, attendi
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)

            result = func(*args, **kwargs)
            last_call = time.time()
            return result

        return wrapper
    return decorator
