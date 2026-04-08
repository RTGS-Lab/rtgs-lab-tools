from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'device_monitoring.db')
print(db_path)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///{}".format(db_path)

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
            "errors": self.errors,
            "is_missing": self.is_missing,
            "last_heard": self.last_heard
            # "particle_url": self.particle_url,
            # "diagnostics": self.diagnostics
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