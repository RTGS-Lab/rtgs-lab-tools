"""
Flask web app wrapper for device monitoring core functionality.
This allows Google Cloud Scheduler to trigger the monitoring via HTTP requests.
"""

import os
from flask import Flask, request, jsonify
from .core import monitor

app = Flask(__name__)

@app.route('/monitor', methods=['POST'])
def run_monitor():
    """
    HTTP endpoint to trigger device monitoring.
    Accepts JSON payload with optional parameters.
    """
    try:
        # Get parameters from request JSON or use defaults
        data = request.get_json() or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date') 
        node_ids = data.get('node_ids')
        project = data.get('project', 'ALL')
        no_email = data.get('no_email', False)
        
        # Call the core monitoring function
        result = monitor(
            start_date=start_date,
            end_date=end_date,
            node_ids=node_ids,
            project=project,
            no_email=no_email
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Device monitoring completed successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)