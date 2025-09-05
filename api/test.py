import os
from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Quick environment and status check
            response = {
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'AI News Automation service is running',
                'environment': {
                    'gemini_key_configured': bool(os.getenv("GEMINI_API_KEY")),
                    'brevo_key_configured': bool(os.getenv("BREVO_API_KEY")),
                    'sender_email_configured': bool(os.getenv("SENDER_EMAIL")),
                    'recipient_emails_configured': bool(os.getenv("RECIPIENT_EMAILS"))
                },
                'optimizations_applied': [
                    'RSS feed timeout: 8 seconds per feed',
                    'Maximum 5 RSS feeds processed',
                    'Maximum 10 entries per feed',
                    'AI processing limited to 10 articles',
                    'Reduced delays between AI requests'
                ]
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
            
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_POST(self):
        self.do_GET()
