"""
Overview:
    - The single place that defines what timezone a timestamp is in.
Rules:
    - GEMS `raw.publish_time` is UTC, and it is the source of every device
      timestamp the parser emits (see data_parser/parsers/base.py).
    - Therefore the pipeline computes and stores everything in UTC.
    - DISPLAY_TIMEZONE is applied only at the edges, when rendering for people.
Why this module exists:
    - The pipeline used to compare `datetime.now()` -- the cluster's local
      Central time -- directly against those UTC device timestamps. Every node
      looked five hours more recent than it really was, so a node had to go
      silent for about 29 hours before the 24-hour missing-node threshold
      fired, and the offset shifted by an hour at each DST boundary.
"""

from datetime import datetime, timezone

from .config import DISPLAY_TIMEZONE

try:
    from zoneinfo import ZoneInfo

    _DISPLAY_TZ = ZoneInfo(DISPLAY_TIMEZONE)
except Exception as exc:  # pragma: no cover - depends on system tzdata
    # A missing tzdata package should degrade to UTC display, not take down the
    # daily report. Everything stays correct; it just reads in UTC.
    print(f"Warning: could not load timezone {DISPLAY_TIMEZONE} ({exc}); displaying UTC")
    _DISPLAY_TZ = timezone.utc


def now_utc():
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def as_utc(value):
    """Normalize a datetime to aware UTC.

    Naive values are assumed to be UTC, which is what GEMS publish_time gives
    us. None passes through so callers can hand over optional timestamps
    without guarding first.
    """
    if value is None or not hasattr(value, "tzinfo"):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_display(value):
    """Convert a UTC (or naive-UTC) datetime into DISPLAY_TIMEZONE."""
    value = as_utc(value)
    if value is None or not hasattr(value, "astimezone"):
        return value
    return value.astimezone(_DISPLAY_TZ)


def format_display(value, fmt="%Y-%m-%d %H:%M:%S", with_zone=True):
    """Render a timestamp in DISPLAY_TIMEZONE, labelled with its zone.

    The zone label is not decoration: without it there is no way to tell a
    Central reading from the UTC value sitting in the database, which is the
    ambiguity that hid this bug in the first place.
    """
    local = to_display(value)
    if local is None:
        return None
    if not hasattr(local, "strftime"):
        return str(local)
    text = local.strftime(fmt)
    if with_zone:
        text = f"{text} {local.strftime('%Z') or DISPLAY_TIMEZONE}"
    return text


def utc_stamp(value=None, fmt="%Y-%m-%d %H:%M"):
    """Format a timestamp for storage. Always UTC, never localized."""
    value = now_utc() if value is None else as_utc(value)
    if value is None or not hasattr(value, "strftime"):
        return None
    return value.strftime(fmt)
