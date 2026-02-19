from flask import Flask, render_template, jsonify, request
from .models import db, Monitoring
from sqlalchemy import func
import os

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rtgs_errors.db'
# db.init_app(app)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'device_monitoring.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db.init_app(app)

@app.route('/')
def index():
    # 1. Get the 'ts' from the URL (this happens when the user clicks the toggle)
    # If it's the first time loading, this will be None.
    selected_ts = request.args.get('ts')

    # 2. Query for ALL unique timestamps for your dropdown
    # .distinct() ensures you don't see the same time 50 times in the menu
    timestamp_query = db.session.query(Monitoring.monitoring_timestamp).distinct().all()
    
    # SQLAlchemy returns a list of tuples like [('2026-01-01',), ('2026-01-02',)]
    # We turn it into a simple list of strings: ['2026-01-01', '2026-01-02']
    timestamps = [t[0] for t in timestamp_query]

    # 3. If no timestamp is selected yet, default to the most recent one
    if not selected_ts and timestamps:
        selected_ts = timestamps[-1]

    # 4. Fetch the data for the specific timestamp to show in the table
    active_data = Monitoring.query.filter_by(monitoring_timestamp=selected_ts).all()

    # 5. PASS THE DATA TO THE TEMPLATE
    return render_template('index.html', 
                           timestamps=timestamps, 
                           active_data=active_data, 
                           selected_ts=selected_ts)
    # return render_template('index.html')

@app.route('/api/monitoring')
def get_fleet_monitoring():
    data = Monitoring.query.all()
    return jsonify([m.to_dict() for m in data])

if __name__ == '__main__':
    app.run(debug=True)