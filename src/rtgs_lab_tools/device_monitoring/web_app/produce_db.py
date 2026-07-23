from datetime import datetime
import json

# from .app import app
from .models import db, Monitoring, LoggerInfo, AppConfig, app
from ..config import (
    BATTERY_VOLTAGE_MIN,
    CRITICAL_ERRORS,
    INBOX_HUMIDITY_MAX,
    SYSTEM_POWER_MAX,
)
from ..message_builder import get_device_info, get_product_slug, get_product_name, get_console_url

def init_db():
    db.create_all()


def build_app_config():
    """Publish the standard config.py defaults into the AppConfig table.

    The web container is isolated from config.py (see Dockerfile), so the daily
    pipeline is what keeps config.py as the single source of truth for defaults:
    it writes them here for the web app to read via /api/config. Per-product
    overrides (ProductConfig) are layered on top of these in the web app and are
    never touched here.
    """
    defaults = {
        "battery_voltage_min": BATTERY_VOLTAGE_MIN,
        "system_power_max": SYSTEM_POWER_MAX,
        "inbox_humidity_max": INBOX_HUMIDITY_MAX,
        "critical_errors": CRITICAL_ERRORS,
    }
    for key, value in defaults.items():
        db.session.merge(AppConfig(config_key=key, config_value=json.dumps(value)))
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Unable to commit app config: {e}")

def build_db(analyzed_data_dict):
    for node_id, data in analyzed_data_dict.items():
        print(data)
        monitor = Monitoring(
            node_id = node_id,
            flagged = data.get("flagged", False),
            battery = data.get("battery"),
            system = data.get("system"),
            humidity = data.get("humidity"),
            errors = json.dumps(data.get("errors", [])),
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
        db.session.rollback()
        print(f'Unable to commit session: {e}')

def build_logger_info(analyzed_data_dict):
    active_node_ids = set(analyzed_data_dict.keys())

    for node_id, data in analyzed_data_dict.items():
        field_name, product_id = get_device_info(node_id)
        product_slug = get_product_slug(product_id)
        product_name = get_product_name(product_id)
        particle_url = get_console_url(node_id, product_id, product_slug)

        monitor = LoggerInfo(
            node_id = node_id,
            field_name = field_name,
            product_name = product_name,
            particle_url = particle_url,
            active = True,
        )
        db.session.merge(monitor)

    # Mark any node not in this run as inactive
    LoggerInfo.query.filter(
        LoggerInfo.node_id.notin_(active_node_ids)
    ).update({LoggerInfo.active: False}, synchronize_session=False)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'Unable to commit session: {e}')