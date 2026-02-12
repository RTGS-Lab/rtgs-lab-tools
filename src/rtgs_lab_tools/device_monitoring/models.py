from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Monitoring(db.Model):
    node_id = db.Column(db.String(255), primary_key=True)
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
            "time of monitoring": self.monitoring_timestamp,
            "time of last device connection": self.device_timestamp,
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