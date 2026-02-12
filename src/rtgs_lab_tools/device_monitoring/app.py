from flask import Flask, render_template, jsonify
from .models import db, Monitoring
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rtgs_errors.db'
db.init_app(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/monitoring')
def get_fleet_monitoring():
    data = Monitoring.query.all()
    return jsonify([m.to_dict() for m in data])

if __name__ == '__main__':
    app.run(debug=True)