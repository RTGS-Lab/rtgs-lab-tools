from datetime import datetime
import json

# from .app import app
from .models import db, Monitoring, app


def build_db(analyzed_data_dict):
    with app.app_context():
        db.create_all()
        for node_id, data in analyzed_data_dict.items():
            monitor = Monitoring(
                node_id = node_id,
                flagged = data.get("flagged", False),
                battery = data.get("battery"),
                system = data.get("system"),
                humidity = data.get("humidity"),
                errors = json.dumps(data.get("errors", {})),
                device_timestamp = (data.get("battery_timestamp") or
                             data.get("system_timestamp") or
                             data.get("humidity_timestamp")).strftime("%Y-%m-%d %H:%M"),
                monitoring_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M"),
                is_missing = data.get("is_missing", False),
                last_heard = data.get("last_heard")
            )
            db.session.add(monitor)
        try:
            db.session.commit()
        except Exception as e:
            print(f'Unable to commit session: {e}')