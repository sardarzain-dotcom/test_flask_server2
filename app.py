from flask import Flask, jsonify, render_template_string
import os

app = Flask(__name__)

# Import chess web interface
try:
    from chess_web import add_chess_routes
    add_chess_routes(app)
    CHESS_AVAILABLE = True
except ImportError as e:
    CHESS_AVAILABLE = False
    print(f"Chess game not available: {e}")

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Basic HTML template for the home page
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Flask Server 2</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { background: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .endpoint { background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Flask Server 2</h1>
        <div class="status">
            <h2>✅ Server Status: Running</h2>
            <p><strong>Deployment URL:</strong> https://testflaskserver2-1010928307866.us-central1.run.app</p>
            <p><strong>Platform:</strong> Google Cloud Run</p>
            <p><strong>Region:</strong> us-central1</p>
        </div>
        
        <h2>Available Endpoints</h2>
        <div class="endpoint">
            <h3>GET /</h3>
            <p>Home page (this page)</p>
        </div>
        <div class="endpoint">
            <h3>GET /chess</h3>
            <p>🎮 <a href="/chess">Play Chess Online!</a></p>
        </div>
        <div class="endpoint">
            <h3>GET /api/health</h3>
            <p>Health check endpoint</p>
        </div>
        <div class="endpoint">
            <h3>GET /api/status</h3>
            <p>Server status information</p>
        </div>
        <div class="endpoint">
            <h3>GET /api/info</h3>
            <p>Application information</p>
        </div>
        <div class="endpoint">
            <h3>GET /api/chess/status</h3>
            <p>Chess game API status</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    """Home page"""
    return render_template_string(HOME_TEMPLATE)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running properly',
        'deployment_url': 'https://testflaskserver2-1010928307866.us-central1.run.app'
    })

@app.route('/api/status')
def status():
    """Server status endpoint"""
    return jsonify({
        'server': 'Test Flask Server 2',
        'status': 'running',
        'deployment': {
            'platform': 'Google Cloud Run',
            'region': 'us-central1',
            'url': 'https://testflaskserver2-1010928307866.us-central1.run.app'
        },
        'environment': os.environ.get('FLASK_ENV', 'development')
    })

@app.route('/api/info')
def app_info():
    """Application information endpoint"""
    return jsonify({
        'name': 'Test Flask Server 2',
        'version': '1.0.0',
        'description': 'A Flask web server for testing purposes',
        'repository': 'Connected to Git repository',
        'deployment': {
            'url': 'https://testflaskserver2-1010928307866.us-central1.run.app',
            'platform': 'Google Cloud Run',
            'region': 'us-central1'
        }
    })

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested endpoint does not exist',
        'available_endpoints': [
            '/',
            '/api/health',
            '/api/status',
            '/api/info'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on the server'
    }), 500

if __name__ == '__main__':
    # Get port from environment variable or default to 5000 for local development
    # Cloud Run uses PORT environment variable
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Run the app
    app.run(host=host, port=port, debug=os.environ.get('FLASK_ENV') == 'development')