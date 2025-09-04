import os
import requests
import feedparser
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent

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
        print(f"An error during summarization: {e}")
        return "<h1>Error: Could not generate summary.</h1>"

def send_email(html_content):
    """Sends the summary email using SendGrid."""
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_emails_str = os.getenv("RECIPIENT_EMAILS")

    if not all([sendgrid_key, sender_email, recipient_emails_str]):
        raise ValueError("Email environment variables not fully set.")

    # Convert the comma-separated string of emails into a list
    recipients = [email.strip() for email in recipient_emails_str.split(',')]
    
    message = Mail(
        from_email=sender_email,
        to_emails=recipients,
        subject='Your Daily AI, ML & Tech Briefing 🚀',
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(sendgrid_key)
        response = sg.send(message)
        print(f"Email sent successfully! Status code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- Vercel Handler Function ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            headlines = fetch_news_articles()
            summary_html = summarize_with_gemini(headlines)
            send_email(summary_html)
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Function executed successfully!")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
        return