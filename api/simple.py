from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Your app is ready! The cron job will work tonight at 11:55 PM!")
    
    def do_POST(self):
        self.do_GET()