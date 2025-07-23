#!/usr/bin/env python3
"""
Simple test server that sets the X-SCYTHE-TARGET-VERSION header.

This server is designed to demonstrate and test the version header extraction
feature in Scythe. It sets the X-SCYTHE-TARGET-VERSION header on all responses
to simulate a real web application that provides version information.

Usage:
    python test_server_with_version.py [port] [version]

Examples:
    python test_server_with_version.py 8080 1.3.2
    python test_server_with_version.py 3000 2.1.0-beta
"""

import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class VersionHeaderServer(BaseHTTPRequestHandler):
    """HTTP request handler that sets version headers on all responses."""
    
    # Class variable to store the version (can be set by server initialization)
    server_version_string = "1.0.0"
    
    def do_GET(self):
        """Handle GET requests."""
        self.handle_request()
    
    def do_POST(self):
        """Handle POST requests."""
        self.handle_request()
    
    def handle_request(self):
        """Handle incoming requests and set version header."""
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Set the version header on all responses
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('X-SCYTHE-TARGET-VERSION', self.server_version_string)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-SCYTHE-TARGET-VERSION')
        self.end_headers()
        
        # Generate response content based on path
        content = self.generate_content(path)
        self.wfile.write(content.encode('utf-8'))
        
        # Log the request
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {self.command} {self.path} - Version: {self.server_version_string}")
    
    def generate_content(self, path):
        """Generate HTML content based on the requested path."""
        
        if path == '/':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Application - Version {self.server_version_string}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .version {{ color: #007acc; font-weight: bold; }}
        .nav {{ margin: 20px 0; }}
        .nav a {{ margin-right: 20px; color: #007acc; text-decoration: none; }}
        .nav a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Application</h1>
        <p class="version">Version: {self.server_version_string}</p>
        <p>This server sets the <code>X-SCYTHE-TARGET-VERSION</code> header to help test Scythe's version detection feature.</p>
    </div>
    
    <div class="nav">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/api/health">API Health</a>
        <a href="/login">Login</a>
        <a href="/dashboard">Dashboard</a>
    </div>
    
    <h2>Welcome to the Test Application</h2>
    <p>This is the home page. Every response from this server includes the version header:</p>
    <pre>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</pre>
    
    <p>Navigate to different pages to see how Scythe captures version information across multiple requests.</p>
</body>
</html>
"""
        
        elif path == '/about':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>About - Test Application</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .version {{ color: #007acc; font-weight: bold; }}
        .nav a {{ margin-right: 20px; color: #007acc; text-decoration: none; }}
    </style>
</head>
<body>
    <h1>About This Test Application</h1>
    <p class="version">Current Version: {self.server_version_string}</p>
    
    <div class="nav">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/api/health">API Health</a>
        <a href="/login">Login</a>
        <a href="/dashboard">Dashboard</a>
    </div>
    
    <h2>Purpose</h2>
    <p>This test server demonstrates Scythe's ability to extract version information from HTTP response headers.</p>
    
    <h2>Features</h2>
    <ul>
        <li>Sets X-SCYTHE-TARGET-VERSION header on all responses</li>
        <li>Provides multiple pages for testing</li>
        <li>Simple HTML interface for manual testing</li>
        <li>Request logging with version information</li>
    </ul>
    
    <h2>Version Information</h2>
    <p>The header <code>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</code> is set on this response.</p>
</body>
</html>
"""
        
        elif path == '/api/health':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>API Health Check</title>
    <style>body {{ font-family: Arial, sans-serif; margin: 40px; }}</style>
</head>
<body>
    <h1>API Health Check</h1>
    <div style="background: #e8f5e8; padding: 20px; border-radius: 5px;">
        <h2>✓ Status: Healthy</h2>
        <p><strong>Version:</strong> {self.server_version_string}</p>
        <p><strong>Timestamp:</strong> {time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Server:</strong> Test Server with Version Headers</p>
    </div>
    
    <div class="nav" style="margin-top: 20px;">
        <a href="/" style="color: #007acc;">← Back to Home</a>
    </div>
    
    <h3>Headers Set</h3>
    <ul>
        <li><code>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</code></li>
        <li><code>Content-Type: text/html</code></li>
        <li><code>Access-Control-Allow-Origin: *</code></li>
    </ul>
</body>
</html>
"""
        
        elif path == '/login':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Login - Test Application</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .form-container {{ max-width: 400px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 3px; }}
        button {{ background: #007acc; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }}
    </style>
</head>
<body>
    <h1>Login to Test Application</h1>
    <p>Version: {self.server_version_string}</p>
    
    <div class="form-container">
        <form>
            <h2>Please Sign In</h2>
            <input type="text" placeholder="Username" name="username">
            <input type="password" placeholder="Password" name="password">
            <button type="submit">Sign In</button>
        </form>
        
        <p style="margin-top: 20px; font-size: 0.9em; color: #666;">
            This is a test login page. The form doesn't actually process credentials,
            but the response includes version header: <code>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</code>
        </p>
    </div>
    
    <div style="text-align: center; margin-top: 20px;">
        <a href="/" style="color: #007acc;">← Back to Home</a>
    </div>
</body>
</html>
"""
        
        elif path == '/dashboard':
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Test Application</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .dashboard-card {{ background: #f9f9f9; padding: 20px; margin: 10px 0; border-radius: 5px; }}
        .version-badge {{ background: #007acc; color: white; padding: 5px 10px; border-radius: 3px; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>Application Dashboard</h1>
    <span class="version-badge">v{self.server_version_string}</span>
    
    <div class="dashboard-card">
        <h3>System Status</h3>
        <p>✓ Application running normally</p>
        <p>✓ Version headers active</p>
        <p>✓ All endpoints responding</p>
    </div>
    
    <div class="dashboard-card">
        <h3>Version Information</h3>
        <p><strong>Current Version:</strong> {self.server_version_string}</p>
        <p><strong>Header:</strong> <code>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</code></p>
        <p>This header is included in all HTTP responses from this server.</p>
    </div>
    
    <div class="dashboard-card">
        <h3>Test Navigation</h3>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <a href="/" style="color: #007acc;">Home</a>
            <a href="/about" style="color: #007acc;">About</a>
            <a href="/api/health" style="color: #007acc;">API Health</a>
            <a href="/login" style="color: #007acc;">Login</a>
            <a href="/dashboard" style="color: #007acc;">Dashboard</a>
        </div>
    </div>
    
    <div class="dashboard-card">
        <h3>Scythe Testing</h3>
        <p>Use this server to test Scythe's version header extraction:</p>
        <pre style="background: #eee; padding: 10px; border-radius: 3px;">python version_header_example.py http://localhost:{getattr(self.server, 'server_port', 8080)}</pre>
    </div>
</body>
</html>
"""
        
        else:
            # 404 page
            self.send_response(404)
            return f"""
<!DOCTYPE html>
<html>
<head>
    <title>404 - Page Not Found</title>
    <style>body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}</style>
</head>
<body>
    <h1>404 - Page Not Found</h1>
    <p>The requested path <code>{path}</code> was not found on this server.</p>
    <p>Version: {self.server_version_string}</p>
    
    <p><a href="/" style="color: #007acc;">← Return to Home</a></p>
    
    <p style="margin-top: 40px; color: #666; font-size: 0.9em;">
        Even 404 responses include the version header: <code>X-SCYTHE-TARGET-VERSION: {self.server_version_string}</code>
    </p>
</body>
</html>
"""
    
    def log_message(self, format, *args):
        """Override to customize logging format."""
        # Suppress default logging (we do our own above)
        pass


def run_server(port=8080, version="1.0.0"):
    """
    Start the test server with version headers.
    
    Args:
        port: Port number to listen on
        version: Version string to include in headers
    """
    # Set the version string on the handler class
    VersionHeaderServer.server_version_string = version
    
    # Create and start the server
    server_address = ('', port)
    httpd = HTTPServer(server_address, VersionHeaderServer)
    
    # Store port on server object for template access
    httpd.server_port = port
    
    print("="*60)
    print("SCYTHE TEST SERVER WITH VERSION HEADERS")
    print("="*60)
    print(f"Server starting on http://localhost:{port}")
    print(f"Version header: X-SCYTHE-TARGET-VERSION: {version}")
    print()
    print("Available endpoints:")
    print(f"  http://localhost:{port}/")
    print(f"  http://localhost:{port}/about")
    print(f"  http://localhost:{port}/api/health")
    print(f"  http://localhost:{port}/login")
    print(f"  http://localhost:{port}/dashboard")
    print()
    print("To test with Scythe:")
    print(f"  python version_header_example.py http://localhost:{port}")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        httpd.server_close()


def main():
    """Main function to parse arguments and start server."""
    # Parse command line arguments
    port = 8080
    version = "1.0.0"
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        version = sys.argv[2]
    
    # Validate port range
    if not (1 <= port <= 65535):
        print(f"Port number must be between 1 and 65535, got: {port}")
        sys.exit(1)
    
    # Start the server
    try:
        run_server(port, version)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Error: Port {port} is already in use.")
            print("Try a different port or stop the service using that port.")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()