from datetime import datetime
import json

# from .app import app
from .models import db, Monitoring, LoggerInfo, app
from ..message_builder import get_device_info, get_product_slug, get_product_name, get_console_url

def init_db():
    db.create_all()

def build_db(analyzed_data_dict):
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

def build_logger_info(analyzed_data_dict):
    for node_id, data in analyzed_data_dict.items():
        field_name, product_id = get_device_info(node_id)
        product_slug = get_product_slug(product_id)
        product_name = get_product_name(product_id)
        particle_url = get_console_url(node_id, product_id, product_slug)

        print(field_name, product_id, product_slug, product_name, particle_url)

        monitor = LoggerInfo(
            node_id = node_id,
            field_name = field_name,
            product_name = product_name,
            particle_url = particle_url
        )
        print(monitor.node_id, monitor.field_name, monitor.product_name, monitor.particle_url)
        db.session.add(monitor)
    try:
        db.session.commit()
    except Exception as e:
        print(f'Unable to commit session: {e}')