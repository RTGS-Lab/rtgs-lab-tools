import hmac
import os

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from .models import db, Monitoring, LoggerInfo, configure_database

basedir = os.path.abspath(os.path.dirname(__file__))
dist_dir = os.path.join(basedir, 'dist')

app = Flask(__name__, static_folder=dist_dir, static_url_path='')
CORS(app)

configure_database(app)
db.init_app(app)

SITE_PASSWORD = os.getenv("DEVICEMON_SITE_PASSWORD")
SITE_USERNAME = os.getenv("DEVICEMON_SITE_USERNAME", "rtgs")

@app.before_request
def require_site_password():
    """Gate the whole site behind a single shared username/password (HTTP Basic Auth).

    Skipped entirely when DEVICEMON_SITE_PASSWORD isn't set, so local dev
    stays open by default.
    """
    if not SITE_PASSWORD:
        return
    auth = request.authorization
    valid = (
        auth
        and hmac.compare_digest(auth.username or "", SITE_USERNAME)
        and hmac.compare_digest(auth.password or "", SITE_PASSWORD)
    )
    if not valid:
        return Response(
            "Authentication required", 401,
            {"WWW-Authenticate": 'Basic realm="Device Monitoring"'},
        )

@app.route('/')
def index():
    return send_from_directory(dist_dir, 'index.html')

@app.route('/api/monitoring')
def get_fleet_monitoring():
    data = Monitoring.query.all()
    return jsonify([m.to_dict() for m in data])

@app.route('/api/logger-info')
def get_logger_info():
    data = LoggerInfo.query.all()
    return jsonify([l.to_dict() for l in data])

@app.route("/api/entries", methods=["GET"])
def get_all_entries():
    """Return all entries, optionally filtered by node_id."""
    node_id = request.args.get("node_id")
    query = Monitoring.query
    if node_id:
        query = query.filter_by(node_id=node_id)
    entries = query.order_by(
        Monitoring.node_id, Monitoring.monitoring_timestamp
    ).all()
    return jsonify([e.to_dict() for e in entries])

@app.route("/api/entries/<node_id>/<path:monitoring_timestamp>", methods=["GET"])
def get_entry(node_id, monitoring_timestamp):
    """Return a single entry by composite primary key."""
    entry = Monitoring.query.get((node_id, monitoring_timestamp))
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    return jsonify(entry.to_dict())


@app.route("/api/nodes", methods=["GET"])
def get_node_ids():
    """Return all distinct node IDs."""
    results = db.session.query(Monitoring.node_id).distinct().all()
    return jsonify([r.node_id for r in results])

if __name__ == '__main__':
    app.run(debug=True, port=5000)