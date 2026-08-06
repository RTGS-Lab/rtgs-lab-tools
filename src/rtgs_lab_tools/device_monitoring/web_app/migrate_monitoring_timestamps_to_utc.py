"""One-time migration: monitoring_timestamp from local Central time to UTC.

Background
----------
Until the timezone fix, `monitoring_timestamp` was written with the cluster's
local clock (`datetime.now()` / `date`), while `device_timestamp` and
`last_heard` came from GEMS publish_time and were already UTC. That is why the
web app showed "last connected" times ahead of the report that produced them.

The pipeline now writes UTC everywhere, so rows written before the fix are five
hours (CDT) or six hours (CST) behind the new ones. This script shifts them
onto the same clock, using the IANA zone so each row gets the offset that was
actually in force on its own date rather than a fixed number.

Safety
------
`monitoring_timestamp` is half of the Monitoring primary key, so this rewrites a
key column. The script therefore:
  * runs read-only by default and prints exactly what it would change
  * refuses to run if any converted value would collide with an existing row
  * only touches rows at or before --cutover, so it can never re-shift a row
    the fixed pipeline wrote

Usage
-----
    # inspect only (default)
    python -m rtgs_lab_tools.device_monitoring.web_app.migrate_monitoring_timestamps_to_utc \
        --cutover "2026-08-06 00:00"

    # apply
    python -m rtgs_lab_tools.device_monitoring.web_app.migrate_monitoring_timestamps_to_utc \
        --cutover "2026-08-06 00:00" --apply
"""

import argparse
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import app, db, Monitoring
from ..config import DISPLAY_TIMEZONE

STAMP_FORMAT = "%Y-%m-%d %H:%M"


def _to_utc_string(local_string, zone):
    """Reinterpret a stored local-time stamp as UTC, honouring DST on its date."""
    naive = datetime.strptime(local_string, STAMP_FORMAT)
    return naive.replace(tzinfo=zone).astimezone(ZoneInfo("UTC")).strftime(STAMP_FORMAT)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cutover",
        required=True,
        # No literal '%' in this text: argparse runs help strings through
        # %-formatting, so spelling out STAMP_FORMAT here raises
        # "badly formed help string" on Python 3.14.
        help=(
            "Only rows with monitoring_timestamp <= this value are migrated. "
            "Give it on the old local clock, as 'YYYY-MM-DD HH:MM' - the stored "
            "values it is compared against are still local-time strings."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the changes. Without it, the script only reports.",
    )
    args = parser.parse_args()

    zone = ZoneInfo(DISPLAY_TIMEZONE)

    with app.app_context():
        rows = (
            Monitoring.query.filter(Monitoring.monitoring_timestamp <= args.cutover)
            .order_by(Monitoring.monitoring_timestamp)
            .all()
        )
        total = Monitoring.query.count()
        print(f"rows in table:        {total}")
        print(f"rows at/before cutover: {len(rows)}")
        if not rows:
            print("Nothing to migrate.")
            return

        existing_keys = {
            (r.node_id, r.monitoring_timestamp) for r in Monitoring.query.all()
        }

        planned = []
        collisions = []
        for row in rows:
            try:
                new_stamp = _to_utc_string(row.monitoring_timestamp, zone)
            except ValueError:
                print(
                    f"  SKIP  {row.node_id} {row.monitoring_timestamp!r} "
                    "- not in the expected format"
                )
                continue
            key = (row.node_id, new_stamp)
            if key in existing_keys and new_stamp != row.monitoring_timestamp:
                collisions.append((row.node_id, row.monitoring_timestamp, new_stamp))
            planned.append((row, new_stamp))

        shifts = Counter(
            f"{old.monitoring_timestamp} -> {new}" for old, new in planned[:5]
        )
        print("\nsample conversions:")
        for line in shifts:
            print(f"  {line}")

        distinct_before = len({r.monitoring_timestamp for r, _ in planned})
        distinct_after = len({new for _, new in planned})
        print(f"\ndistinct timestamps before: {distinct_before}")
        print(f"distinct timestamps after:  {distinct_after}")

        if collisions:
            print(f"\nABORT: {len(collisions)} converted rows collide with existing rows:")
            for node_id, old, new in collisions[:10]:
                print(f"  {node_id}: {old} -> {new}")
            print("No changes written.")
            return

        if not args.apply:
            print(f"\nDry run. {len(planned)} rows would be rewritten. Re-run with --apply.")
            return

        # The primary key itself changes, so delete-then-insert rather than
        # mutating in place: SQLAlchemy cannot UPDATE a row's identity.
        for row, new_stamp in planned:
            replacement = Monitoring(
                node_id=row.node_id,
                monitoring_timestamp=new_stamp,
                device_timestamp=row.device_timestamp,
                flagged=row.flagged,
                battery=row.battery,
                system=row.system,
                humidity=row.humidity,
                errors=row.errors,
                is_missing=row.is_missing,
                last_heard=row.last_heard,
            )
            db.session.delete(row)
            db.session.flush()
            db.session.add(replacement)

        db.session.commit()
        print(f"\nMigrated {len(planned)} rows to UTC.")


if __name__ == "__main__":
    main()
