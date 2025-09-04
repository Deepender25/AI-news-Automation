import os
import requests
import feedparser
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

# --- Configuration ---
RSS_FEEDS = [
    # A curated list of AI, ML, and Tech news feeds
    "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/", "http://feeds.feedburner.com/AINews",
    "https://www.wired.com/feed/tag/ai/latest/rss", "https://marktechpost.com/feed/",
    "https://research.google/blog/rss/", "https://bair.berkeley.edu/blog/feed.xml",
]

# --- Core Functions ---

def fetch_news_articles():
    all_headlines = set()
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: all_headlines.add(entry.title)
        except Exception as e: print(f"Error fetching feed {url}: {e}")
    return "\n".join(all_headlines)

def summarize_with_gemini(headlines_text):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not headlines_text: return "No new AI, ML, or Tech news found today."
    if not gemini_api_key: raise ValueError("GEMINI_API_KEY not found.")
    
    print("Summarizing with Gemini...")
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = (
            "You are an expert tech analyst. Synthesize a daily briefing from these headlines. "
            "Format your entire response in simple HTML. Use <h1> for a main title, <h2> for subtitles "
            "(like 'Top Story' or 'AI & Machine Learning'), and <ul>/<li> for bullet points. "
            "Be concise and insightful. Headlines:\n"
            f"{headlines_text}"
        )
        response = model.generate_content(prompt)
        print("Summary generated successfully.")
        return response.text
    except Exception as e:
        return f"<h1>Error: Could not generate summary. Details: {e}</h1>"

def send_email_with_brevo(html_content):
    """Sends the summary email using the Brevo (Sendinblue) API."""
    brevo_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_emails_str = os.getenv("RECIPIENT_EMAILS")

    if not all([brevo_key, sender_email, recipient_emails_str]):
        raise ValueError("Email environment variables not fully set.")

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = brevo_key
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = {"email": sender_email}
    recipients = [{"email": email.strip()} for email in recipient_emails_str.split(',')]
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=recipients,
        html_content=html_content,
        sender=sender,
        subject='Your Daily AI, ML & Tech Briefing 🚀'
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print("Email sent successfully via Brevo!")
    except ApiException as e:
        print(f"Failed to send email via Brevo: {e}")

# --- Vercel Handler Function ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            headlines = fetch_news_articles()
            summary_html = summarize_with_gemini(headlines)
            send_email_with_brevo(summary_html)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Function executed successfully!")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
        return