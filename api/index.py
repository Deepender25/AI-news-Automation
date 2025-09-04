import os
import feedparser
import google.generativeai as genai
from http.server import BaseHTTPRequestHandler
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timedelta
import re

# --- Enhanced Core Functions ---
def fetch_news_articles():
    """Fetch AI news from comprehensive RSS feed list"""
    RSS_FEEDS = [
        # Core AI/ML News
        "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "http://feeds.feedburner.com/AINews",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://marktechpost.com/feed/",
        "https://ai-techpark.com/category/ai/feed/",
        "https://knowtechie.com/category/ai/feed/",
        # Academic & Research
        "https://research.google/blog/rss/",
        "https://bair.berkeley.edu/blog/feed.xml",
        "https://magazine.sebastianraschka.com/feed",
        # Broader Tech News
        "https://www.404media.co/rss/",
        "https://ai2people.com/feed/",
    ]
    
    all_articles = []
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Get article date
                article_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article_date = datetime(*entry.published_parsed[:6]).date()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    article_date = datetime(*entry.updated_parsed[:6]).date()
                
                # Include articles from today and yesterday
                if article_date and article_date >= yesterday:
                    all_articles.append({
                        'title': entry.title,
                        'link': entry.link if hasattr(entry, 'link') else '',
                        'summary': entry.summary if hasattr(entry, 'summary') else '',
                        'date': article_date,
                        'source': extract_domain(url)
                    })
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
    
    # Remove duplicates based on title similarity
    unique_articles = remove_duplicates(all_articles)
    return unique_articles[:50]  # Limit to 50 most recent articles

def extract_domain(url):
    """Extract domain name from URL for source attribution"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace('www.', '').replace('feeds.', '')
    except:
        return "Unknown"

def remove_duplicates(articles):
    """Remove duplicate articles based on title similarity"""
    unique_articles = []
    seen_titles = set()
    
    for article in articles:
        # Create a normalized version of the title for comparison
        normalized_title = re.sub(r'[^a-zA-Z0-9\s]', '', article['title'].lower()).strip()
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_articles.append(article)
    
    return unique_articles

def summarize_with_gemini(articles):
    """Create detailed AI summaries with bold key topics"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not articles: 
        return []
    if not gemini_api_key: 
        return articles[:15]  # Return articles without AI summaries
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create individual summaries for each article
        summarized_articles = []
        
        # Process articles in smaller batches to avoid rate limits
        for i, article in enumerate(articles[:15]):
            try:
                # Add a small delay to avoid rate limiting
                if i > 0 and i % 5 == 0:
                    import time
                    time.sleep(2)  # 2-second pause every 5 articles
                
                # Create prompt for topic summary (not article content)
                prompt = f"""Create a clear, concise 4-5 line summary explaining WHAT this topic is about and WHY it matters in AI/technology.

DO NOT summarize the article content. Instead, explain the TOPIC itself.

FORMATTING RULES:
- Write 4-5 lines maximum
- Explain what this technology/topic/development is
- Explain why it's significant in AI/tech
- Use simple, clear language
- Do not use bold formatting or special characters
- Make it educational about the topic, not a news summary

Title: {article['title']}
Source: {article['source']}

Provide a 4-5 line explanation of what this topic is about and its significance:"""
                
                response = model.generate_content(prompt)
                
                if response and response.text and response.text.strip():
                    ai_summary = response.text.strip()
                    # Ensure we have a proper detailed summary
                    if len(ai_summary) > 100 and "visit the link" not in ai_summary.lower():
                        enhanced_article = article.copy()
                        enhanced_article['ai_summary'] = ai_summary
                        summarized_articles.append(enhanced_article)
                        continue
                
                # If AI summary failed, create a detailed fallback
                enhanced_article = article.copy()
                fallback_summary = create_detailed_fallback_summary(article)
                enhanced_article['ai_summary'] = fallback_summary
                summarized_articles.append(enhanced_article)
                
            except Exception as e:
                print(f"Error summarizing article {article['title']}: {e}")
                # Add article with detailed fallback
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_detailed_fallback_summary(article)
                summarized_articles.append(enhanced_article)
        
        return summarized_articles
        
    except Exception as e:
        print(f"Gemini AI error: {e}")
        # Return articles with detailed fallback summaries
        fallback_articles = []
        for article in articles[:15]:
            enhanced_article = article.copy()
            enhanced_article['ai_summary'] = create_detailed_fallback_summary(article)
            fallback_articles.append(enhanced_article)
        return fallback_articles

def create_detailed_fallback_summary(article):
    """Create a detailed fallback summary when AI fails"""
    title = article['title']
    original_summary = article.get('summary', '')
    
    # Try to extract company/product names for bold formatting (without quotes)
    companies = ['OpenAI', 'Google', 'Microsoft', 'Meta', 'Apple', 'Amazon', 'Tesla', 'NVIDIA', 'Adobe', 'IBM', 'Anthropic']
    models = ['GPT-4', 'GPT-3', 'Claude', 'Gemini', 'Bard', 'ChatGPT', 'Copilot', 'DALL-E', 'Midjourney']
    
    formatted_title = title
    for company in companies:
        if company.lower() in title.lower():
            formatted_title = formatted_title.replace(company, f'**{company}**')
    
    for model in models:
        if model.lower() in title.lower():
            formatted_title = formatted_title.replace(model, f'**{model}**')
    
    if original_summary and len(original_summary) > 200:
        # Create a comprehensive summary using original content
        summary_text = original_summary[:400]
        # Add bold formatting to key terms in the summary
        for company in companies:
            if company.lower() in summary_text.lower():
                summary_text = summary_text.replace(company, f'**{company}**')
        for model in models:
            if model.lower() in summary_text.lower():
                summary_text = summary_text.replace(model, f'**{model}**')
        
        return f"""This article covers developments regarding {formatted_title}.

{summary_text}

This represents significant progress in the **artificial intelligence** and technology sector. The advancement demonstrates the ongoing evolution of **machine learning** capabilities and could have important implications for businesses, developers, and end users. The development highlights the competitive landscape in AI technology and the rapid pace of innovation in this field.

The implications of this advancement extend beyond the immediate technical achievements, potentially influencing industry standards and future development directions in the **AI** space."""
    else:
        # Create detailed summary based on title analysis
        return f"""This article discusses significant developments related to {formatted_title}.

The announcement represents a notable advancement in the **artificial intelligence** and technology sector. This development showcases the ongoing innovation in **machine learning** and demonstrates the competitive dynamics within the AI industry.

The advancement has potential implications for various stakeholders including developers, businesses, and end users who rely on AI-powered solutions. The development reflects the rapid pace of progress in **AI technology** and suggests continued evolution in this space.

This represents part of the broader trend of technological advancement and innovation that is reshaping how we interact with and benefit from **artificial intelligence** systems. The implications may extend beyond the immediate technical achievements to influence future industry directions.

The development underscores the importance of staying informed about AI advancements as they continue to impact various sectors and applications."""

def create_fallback_summary(article):
    """Legacy fallback - redirects to detailed version"""
    return create_detailed_fallback_summary(article)

def create_daily_email(articles):
    """Create ultra-simple modern email template"""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    
    # Create simple articles text
    articles_text = ""
    
    for i, article in enumerate(articles, 1):
        # Clean and format article data
        title = article.get('title', 'Untitled Article').strip()
        link = article.get('link', '#').strip()
        source = article.get('source', 'Unknown').replace('.com', '').replace('feedburner', 'AI News').replace('www.', '').title()
        
        # Get brief AI summary (4-5 lines max)
        summary_text = article.get('ai_summary', '')
        if not summary_text:
            summary_text = "This topic covers important developments in artificial intelligence and technology."
        
        # Ensure summary is 4-5 lines maximum
        lines = summary_text.split('\n')
        if len(lines) > 5:
            summary_text = '\n'.join(lines[:5])
        
        # Clean summary text and remove all formatting
        summary_text = summary_text.replace('**', '').replace('*', '').strip()
        
        articles_text += f"""

{i}. {title}

{current_date} | Source: {source}

{summary_text}

Read Full Article: {link}

{'-' * 80}
        """
    
    # Create plain text email with minimal HTML
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Technology News - {current_date}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.5; color: #000000; margin: 20px; background-color: #ffffff;">
    
    <h1>AI Technology News</h1>
    <p>{weekday}, {current_date}</p>
    <p>{len(articles)} articles</p>
    
    <hr>
    
    <div style="white-space: pre-line;">{articles_text}</div>
    
    <hr>
    
    <p><small>AI-generated topic summaries | Delivered daily at 1:00 AM IST</small></p>
    
</body>
</html>
    """

def send_daily_email(articles):
    """Send single daily email with all articles"""
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
    
    # Create daily email content with all articles
    html_content = create_daily_email(articles)
    
    # Create dynamic subject line with date and article count (changes daily)
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    subject = f"AI Technology News - {weekday}, {current_date} ({len(articles)} articles)"
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=recipients,
        html_content=html_content,
        sender=sender,
        subject=subject
    )

    api_instance.send_transac_email(send_smtp_email)
    return True

# --- Vercel Handler Function ---
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Check if this is a test endpoint
            if hasattr(self, 'path') and '/test' in self.path:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                # Quick environment check
                env_check = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'gemini_key_set': bool(os.getenv("GEMINI_API_KEY")),
                    'brevo_key_set': bool(os.getenv("BREVO_API_KEY")),
                    'sender_email_set': bool(os.getenv("SENDER_EMAIL")),
                    'recipient_emails_set': bool(os.getenv("RECIPIENT_EMAILS")),
                    'status': 'Environment configured'
                }
                
                import json
                self.wfile.write(json.dumps(env_check).encode())
                return
            
            # Fetch news articles
            articles = fetch_news_articles()
            if not articles:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"No articles found today.")
                return
            
            # Generate AI summaries for each article
            summarized_articles = summarize_with_gemini(articles)
            
            # Send single daily email with all articles
            try:
                send_daily_email(summarized_articles)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Success! Daily email sent with {len(summarized_articles)} articles at {datetime.utcnow().isoformat()}.".encode())
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Failed to send daily email: {str(e)}".encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())
    
    def do_POST(self):
        self.do_GET()
