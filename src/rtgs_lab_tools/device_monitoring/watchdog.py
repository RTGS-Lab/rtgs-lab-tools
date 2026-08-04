"""
Overview:
    - Per-step watchdog timers for the daily monitoring pipeline.
Why this exists:
    - Every remote call the pipeline makes (the GEMS query, the Cloud SQL
      writes, the SMTP send) can block forever, because none of the underlying
      clients set a socket timeout. When that happens the run neither finishes
      nor fails: cron sees nothing to retry and the day's data is lost silently.
    - Wrapping each step in `step_timeout` converts an indefinite stall into a
      StepTimeout exception, which surfaces in the log and gives the shell
      wrapper a non-zero exit code to retry on.
Limitations:
    - Implemented with SIGALRM, so it only fires on POSIX and only in the main
      thread. On platforms without SIGALRM (Windows) it is a no-op and the
      `timeout` wrapper in scheduled_device_monitoring.sh is the only backstop.
    - SIGALRM interrupts a blocking syscall, so it unblocks a stuck socket, but
      it cannot interrupt a C extension that holds the GIL without checking
      signals. The shell-level timeout covers that case.
"""

import signal
from contextlib import contextmanager

_SIGALRM_AVAILABLE = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")


class StepTimeout(Exception):
    """Raised when a pipeline step exceeds its allotted wall-clock time."""


@contextmanager
def step_timeout(seconds, description):
    """Raise StepTimeout if the wrapped block runs longer than `seconds`.

    Args:
        seconds: Wall-clock limit. None or a non-positive value disables the
            watchdog, which is also what happens where SIGALRM is unavailable.
        description: Step name used in the exception message.
    """
    if not _SIGALRM_AVAILABLE or not seconds or seconds <= 0:
        yield
        return

    def _on_alarm(signum, frame):
        raise StepTimeout(
            f"{description} exceeded its {seconds}s limit and was aborted. "
            "This usually means a remote service (GEMS database, Cloud SQL, or "
            "SMTP) stopped responding mid-call."
        )

    previous_handler = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
