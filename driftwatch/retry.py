import logging
import time

logger = logging.getLogger("driftwatch")


def with_retry(func, *args, max_attempts=3, base_delay=2, **kwargs):
    """Retry a function call with exponential backoff."""
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
    raise last_exception
