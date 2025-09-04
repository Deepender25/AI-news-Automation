import os
import sib_api_v3_sdk
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Just send a simple test email
            brevo_key = os.getenv("BREVO_API_KEY")
            sender_email = os.getenv("SENDER_EMAIL")
            recipient_emails_str = os.getenv("RECIPIENT_EMAILS")

            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = brevo_key
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

            sender = {"email": sender_email}
            recipients = [{"email": email.strip()} for email in recipient_emails_str.split(',')]
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=recipients,
                html_content="<h1>🧪 Test Successful!</h1><p>Your AI News Automation is working perfectly! The cron job will run tonight at 11:55 PM.</p>",
                sender=sender,
                subject='✅ TEST SUCCESS - AI News Automation Works!'
            )

            api_instance.send_transac_email(send_smtp_email)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"SUCCESS! Test email sent. Check your inbox!")
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())
    
    def do_POST(self):
        self.do_GET()