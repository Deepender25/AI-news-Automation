import os
import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """
        Handles GET requests to check the environment variable configuration.
        """
        # Define the list of required environment variables
        required_vars = [
            "GEMINI_API_KEY",
            "BREVO_API_KEY",
            "SENDER_EMAIL",
            "RECIPIENT_EMAILS"
        ]

        # Check which variables are set
        env_status = {var: bool(os.getenv(var)) for var in required_vars}
        all_vars_set = all(env_status.values())

        # Create a user-friendly message and instructions
        if all_vars_set:
            message = "All environment variables are configured correctly."
            instructions = "Your application appears to be set up properly. If you're still experiencing issues, check the Vercel function logs for runtime errors."
        else:
            missing_vars = [var for var, is_set in env_status.items() if not is_set]
            message = f"Action required: The following environment variables are missing: {', '.join(missing_vars)}."
            instructions = "Please go to your project settings in the Vercel dashboard, click on 'Environment Variables', and add the missing values. Make sure the variable names are spelled correctly."

        # Prepare the JSON response
        response_data = {
            "status": "success" if all_vars_set else "error",
            "message": message,
            "instructions": instructions,
            "environment_check": {
                var: "✅ Set" if is_set else "❌ Missing"
                for var, is_set in env_status.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send headers and the JSON response
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, indent=2).encode('utf-8'))

    def do_POST(self):
        """
        Handles POST requests by calling the GET handler.
        """
        self.do_GET()
