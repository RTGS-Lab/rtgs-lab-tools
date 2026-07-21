from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import os

from dotenv import load_dotenv

# NOTE: This module is deployed to Cloud Run in an isolated image that contains
# only models.py + app.py (see Dockerfile). It must NOT import anything from the
# wider rtgs_lab_tools package (e.g. ..config), or the container will fail to
# import. Config values the frontend needs (thresholds, critical error list) are
# written into the AppConfig table by the daily pipeline and served via /api/config.

load_dotenv()


def configure_database(flask_app):
    """Point flask_app at the Cloud SQL Postgres instance if configured,
    otherwise fall back to a local SQLite file for local development."""
    instance_connection_name = os.getenv("DEVICEMON_INSTANCE_CONNECTION_NAME")

    if instance_connection_name:
        import pg8000
        from google.cloud.sql.connector import Connector, IPTypes

        connector = Connector()

        def getconn():
            return connector.connect(
                instance_connection_name,
                "pg8000",
                user=os.getenv("DEVICEMON_DB_USER", "devicemon_app"),
                password=os.getenv("DEVICEMON_DB_PASSWORD"),
                db=os.getenv("DEVICEMON_DB_NAME", "device_monitoring"),
                ip_type=IPTypes.PUBLIC,
            )

        flask_app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+pg8000://"
        flask_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "creator": getconn,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'instance', 'device_monitoring.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)        # create a new database if it doesn't exist
        flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///{}".format(db_path)


app = Flask(__name__)
configure_database(app)

db = SQLAlchemy(app)

class Monitoring(db.Model):
    node_id = db.Column(db.String(50), primary_key=True)
    monitoring_timestamp = db.Column(db.String(30), primary_key=True) # "YYYY-MM-DD HH:MM:SS.SSS"
    device_timestamp = db.Column(db.String(30), nullable=True) # "YYYY-MM-DD HH:MM:SS.SSS"
    flagged = db.Column(db.String(20), nullable=False)
    battery = db.Column(db.Float, nullable=False)
    system = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    errors = db.Column(db.String(1023), nullable=False)
    is_missing = db.Column(db.String(20), nullable=False)
    last_heard = db.Column(db.String(30), nullable=False) # "YYYY-MM-DD HH:MM:SS.SSS"

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "monitoring_timestamp": self.monitoring_timestamp,
            "time_of_last_device_connection": self.device_timestamp,
            "flagged": self.flagged,
            "battery": self.battery,
            "system": self.system,
            "humidity": self.humidity,
            # Raw metrics + errors are returned as-is; the frontend derives the
            # list of flagging "problems" from these using the (possibly
            # per-product) config served by /api/config and /api/product-config.
            "errors": self.errors,
            "is_missing": self.is_missing,
            "last_heard": self.last_heard
            # "particle_url": self.particle_url,
            # "diagnostics": self.diagnostics
        }


class IgnoredProblem(db.Model):
    """A problem a user has chosen to silence for a given node.

    A device is only shown as OK when every one of its currently-active
    problems has a matching row here (or it has no active problems at all).
    An ignore persists until a user explicitly clears it.
    """
    node_id = db.Column(db.String(50), primary_key=True)
    # Matches a key produced by derive_problems: "battery", "system",
    # "humidity", "missing", or "error:<ERROR_NAME>".
    problem_key = db.Column(db.String(120), primary_key=True)
    ignored_at = db.Column(db.String(30), nullable=True)  # when the ignore was set
    ignored_by = db.Column(db.String(120), nullable=True)  # Basic Auth username

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "problem_key": self.problem_key,
            "ignored_at": self.ignored_at,
            "ignored_by": self.ignored_by,
        }


class AppConfig(db.Model):
    """Global default configuration, written by the daily pipeline from
    config.py. Keeps config.py as the single source of truth for defaults while
    letting the isolated web container read them without importing config.py.

    Keys: "battery_voltage_min", "system_power_max", "inbox_humidity_max",
    "critical_errors" (the value is JSON-encoded).
    """
    config_key = db.Column(db.String(50), primary_key=True)
    config_value = db.Column(db.String(4095), nullable=False)  # JSON-encoded

    def to_dict(self):
        return {"config_key": self.config_key, "config_value": self.config_value}


class ProductConfig(db.Model):
    """Per-product overrides of the global defaults, edited from the web app's
    Configuration tab. A row exists only for keys a product actually overrides;
    everything else falls back to AppConfig. Same keys/value encoding as
    AppConfig.
    """
    product_name = db.Column(db.String(50), primary_key=True)
    config_key = db.Column(db.String(50), primary_key=True)
    config_value = db.Column(db.String(4095), nullable=False)  # JSON-encoded

    def to_dict(self):
        return {
            "product_name": self.product_name,
            "config_key": self.config_key,
            "config_value": self.config_value,
        }


class LoggerInfo(db.Model):
    node_id = db.Column(db.String(50), primary_key=True)
    field_name = db.Column(db.String(50), nullable=False)   # ex. "WinterTurf_Type_A_64"
    product_name = db.Column(db.String(50), nullable=False) # ex. "Winter Turf - v3"
    particle_url = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "field_name": self.field_name,
            "product_name": self.product_name,
            "particle_url": self.particle_url,
            "active": self.active,
        }