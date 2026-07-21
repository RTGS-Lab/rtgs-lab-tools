import hmac
import json
import os
from datetime import datetime

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from .models import (
    db,
    Monitoring,
    LoggerInfo,
    IgnoredProblem,
    AppConfig,
    ProductConfig,
    configure_database,
)

# Config keys that may be overridden per product from the Configuration tab.
EDITABLE_CONFIG_KEYS = {
    "battery_voltage_min",
    "system_power_max",
    "inbox_humidity_max",
    "critical_errors",
}

basedir = os.path.abspath(os.path.dirname(__file__))
dist_dir = os.path.join(basedir, 'dist')

app = Flask(__name__, static_folder=dist_dir, static_url_path='')
CORS(app)

configure_database(app)
db.init_app(app)

# Ensure tables exist (idempotent; only creates missing tables such as
# IgnoredProblem so the web app works even before the next pipeline run).
with app.app_context():
    db.create_all()

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


def _decode_config_value(raw):
    """Config values are stored JSON-encoded; fall back to the raw string."""
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return the global default config (written by the daily pipeline).

    Shape: {"battery_voltage_min": 3.6, ..., "critical_errors": [...]}.
    """
    rows = AppConfig.query.all()
    return jsonify({r.config_key: _decode_config_value(r.config_value) for r in rows})


@app.route("/api/product-config", methods=["GET"])
def get_product_config():
    """Return per-product overrides grouped by product name.

    Shape: {"Winter Turf - v3": {"battery_voltage_min": 3.5}, ...}.
    """
    grouped = {}
    for r in ProductConfig.query.all():
        grouped.setdefault(r.product_name, {})[r.config_key] = _decode_config_value(
            r.config_value
        )
    return jsonify(grouped)


@app.route("/api/product-config", methods=["PUT"])
def set_product_config():
    """Apply config overrides to one or more products at once.

    Body: {"product_names": [...], "overrides": {key: value, ...}}.
    A value of null clears that override for the products (revert to default).
    """
    body = request.get_json(silent=True) or {}
    product_names = body.get("product_names") or []
    overrides = body.get("overrides") or {}

    if not product_names:
        return jsonify({"error": "product_names is required"}), 400

    bad_keys = set(overrides) - EDITABLE_CONFIG_KEYS
    if bad_keys:
        return jsonify({"error": f"Unknown config keys: {sorted(bad_keys)}"}), 400

    for product_name in product_names:
        for key, value in overrides.items():
            if value is None:
                # Clear the override -> revert this product/key to the default.
                existing = ProductConfig.query.get((product_name, key))
                if existing:
                    db.session.delete(existing)
            else:
                db.session.merge(
                    ProductConfig(
                        product_name=product_name,
                        config_key=key,
                        config_value=json.dumps(value),
                    )
                )

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unable to save product config: {e}"}), 500

    return get_product_config()


@app.route("/api/ignored-problems", methods=["GET"])
def get_ignored_problems():
    """Return ignored problems, optionally filtered by node_id."""
    node_id = request.args.get("node_id")
    query = IgnoredProblem.query
    if node_id:
        query = query.filter_by(node_id=node_id)
    return jsonify([i.to_dict() for i in query.all()])


@app.route("/api/ignored-problems", methods=["POST"])
def add_ignored_problem():
    """Ignore a problem for a node. Body: {node_id, problem_key}."""
    body = request.get_json(silent=True) or {}
    node_id = body.get("node_id")
    problem_key = body.get("problem_key")
    if not node_id or not problem_key:
        return jsonify({"error": "node_id and problem_key are required"}), 400

    auth = request.authorization
    ignored_by = auth.username if auth else None

    ignore = IgnoredProblem(
        node_id=node_id,
        problem_key=problem_key,
        ignored_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ignored_by=ignored_by,
    )
    db.session.merge(ignore)  # upsert on the composite primary key
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unable to save ignore: {e}"}), 500
    return jsonify(ignore.to_dict()), 201


@app.route("/api/ignored-problems/<node_id>/<path:problem_key>", methods=["DELETE"])
def delete_ignored_problem(node_id, problem_key):
    """Un-ignore a problem for a node."""
    ignore = IgnoredProblem.query.get((node_id, problem_key))
    if not ignore:
        return jsonify({"error": "Ignore not found"}), 404
    db.session.delete(ignore)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unable to remove ignore: {e}"}), 500
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)