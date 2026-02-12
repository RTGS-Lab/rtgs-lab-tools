from datetime import datetime
import json

from .app import app
from .models import db, Monitoring


def build_db(analyzed_data_dict):
    print("inside function")
    # try:
    #     from .app import app
    #     from .models import db, Monitoring
    # except ImportError as e:
    #     print(f'Import error: {e}')
    #     raise
    # except Exception as e:
    #     print(f'General error during import: {e}')
    print("next step")
    with app.app_context():
        print("inside app.context")
        db.create_all()
        # print(analyzed_data_dict)
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
            print("added session")
        try:
            db.session.commit()
        except Exception as e:
            print(f'Unable to commit session: {e}')

# if __name__ == "__main__":
    # nodes = parse_error_file('errors.txt')
    # build_db(nodes)