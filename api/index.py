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
    """Fetch AI news from comprehensive RSS feed list with timeouts"""
    import socket
    
    # Prioritized RSS feeds (most reliable sources first)
    RSS_FEEDS = [
        # Core AI/ML News (most reliable)
        "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://marktechpost.com/feed/",
        # Academic & Research  
        "https://research.google/blog/rss/",
        # Additional sources for more content
        "http://feeds.feedburner.com/AINews",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://ai-techpark.com/category/ai/feed/",
        # Extra feeds for better coverage
        "https://bair.berkeley.edu/blog/feed.xml",
        "https://www.404media.co/rss/",
        "https://ai2people.com/feed/"
    ]
    
    all_articles = []
    today = datetime.utcnow().date()
    three_days_ago = today - timedelta(days=3)  # Extended to 3 days for more articles
    
    # Set global socket timeout for RSS requests
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(5)  # Reduced to 5 seconds per feed
    
    # Process only first 3 feeds to avoid timeout issues
    feeds_to_process = RSS_FEEDS[:3]  # Reduced from 5 to 3
    
    try:
        for url in feeds_to_process:
            try:
                # Parse feed with built-in timeout via socket setting
                feed = feedparser.parse(url)
                
                # Quick check if feed is valid
                if not hasattr(feed, 'entries') or not feed.entries:
                    continue
                    
                for entry in feed.entries[:10]:  # Limit entries per feed
                    # Get article date
                    article_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            article_date = datetime(*entry.published_parsed[:6]).date()
                        except (TypeError, ValueError):
                            continue
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        try:
                            article_date = datetime(*entry.updated_parsed[:6]).date()
                        except (TypeError, ValueError):
                            continue
                    
                    # Include articles from the last 3 days
                    if article_date and article_date >= three_days_ago:
                        all_articles.append({
                            'title': getattr(entry, 'title', 'No Title'),
                            'link': getattr(entry, 'link', ''),
                            'summary': getattr(entry, 'summary', '')[:500],  # Limit summary length
                            'date': article_date,
                            'source': extract_domain(url)
                        })
                        
                        # Stop early if we have enough articles
                        if len(all_articles) >= 30:
                            break
                            
            except Exception as e:
                print(f"Error fetching feed {url}: {e}")
                continue  # Continue with next feed
                
            # Early exit if we have enough articles
            if len(all_articles) >= 30:
                break
                
    finally:
        # Restore original timeout
        socket.setdefaulttimeout(original_timeout)
    
    # Remove duplicates based on title similarity
    unique_articles = remove_duplicates(all_articles)
    return unique_articles[:30]  # Increase to ensure we get at least 10-15 articles

def extract_domain(url):
    """Extract clean, readable domain name from URL for source attribution"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Clean up domain name
        domain = domain.replace('www.', '').replace('feeds.', '').replace('feed.', '')
        
        # Create more readable source names
        source_mapping = {
            'technologyreview.com': 'MIT Technology Review',
            'venturebeat.com': 'VentureBeat',
            'marktechpost.com': 'MarkTechPost',
            'research.google': 'Google Research',
            'feedburner.com': 'AI News',
            'wired.com': 'Wired',
            'ai-techpark.com': 'AI TechPark',
            'bair.berkeley.edu': 'Berkeley AI Research',
            'magazine.sebastianraschka.com': 'Sebastian Raschka',
            '404media.co': '404 Media',
            'ai2people.com': 'AI2People'
        }
        
        # Return mapped name if available, otherwise cleaned domain
        return source_mapping.get(domain, domain.capitalize())
        
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
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Create individual summaries for each article
        summarized_articles = []
        
        # Process fewer articles to avoid timeout
        articles_to_process = articles[:8]  # Reduced to 8 articles for faster processing
        
        for i, article in enumerate(articles_to_process):
            try:
                # Minimal delay to avoid rate limiting
                if i > 0 and i % 8 == 0:
                    import time
                    time.sleep(1)  # Reduced from 2 to 1 second
                
                # Create prompt for concise, informative summary
                prompt = f"""Create a brief, informative summary (3-4 sentences) that gives readers enough knowledge to understand what this article is about without needing to read the full piece.

REQUIREMENTS:
- Write 3-4 sentences maximum
- Focus on the key facts, developments, or announcements
- Explain what happened, who is involved, and why it matters
- Use clear, professional language
- No bold formatting or special characters
- Make it informative enough that readers get the main points

Title: {article['title']}
Source: {article['source']}
Original content: {article.get('summary', '')[:300]}

Provide a concise summary that captures the essential information:"""
                
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
    """Create a concise fallback summary when AI fails"""
    title = article['title']
    original_summary = article.get('summary', '')
    
    if original_summary and len(original_summary) > 100:
        # Use the original summary but make it concise
        sentences = original_summary.split('. ')
        if len(sentences) >= 3:
            summary_text = '. '.join(sentences[:3]) + '.'
        else:
            summary_text = original_summary[:300] + '...' if len(original_summary) > 300 else original_summary
        
        return f"This article discusses {title.lower()}. {summary_text} This development represents important progress in the artificial intelligence and technology sector."
    else:
        # Create a basic summary based on title
        return f"This article covers recent developments related to {title.lower()}. The announcement highlights significant progress in artificial intelligence and technology. This advancement demonstrates the ongoing innovation in the AI sector and its potential impact on the industry."

def create_fallback_summary(article):
    """Legacy fallback - redirects to detailed version"""
    return create_detailed_fallback_summary(article)

def create_daily_email(articles):
    """Create clean, professional email template"""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    
    # Create articles HTML
    articles_html = ""
    
    for i, article in enumerate(articles, 1):
        # Clean and format article data
        title = article.get('title', 'Untitled Article').strip()
        link = article.get('link', '#').strip()
        source = article.get('source', 'Unknown Source').strip()
        
        # Format the article date
        article_date = article.get('date')
        if article_date:
            if hasattr(article_date, 'strftime'):
                date_str = article_date.strftime("%B %d, %Y")
            else:
                date_str = str(article_date)
        else:
            date_str = "Date not available"
        
        # Get AI summary and clean it
        summary_text = article.get('ai_summary', '')
        if not summary_text:
            summary_text = "This article covers important developments in artificial intelligence and technology that are shaping the industry today."
        
        # Clean summary text - remove markdown formatting but keep content readable
        summary_text = summary_text.replace('**', '').replace('*', '').strip()
        
        # Ensure summary is concise but informative
        if len(summary_text) > 500:
            sentences = summary_text.split('. ')
            summary_text = '. '.join(sentences[:3]) + '.'
        
        articles_html += f"""
        <div style="margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #e0e0e0;">
            <h2 style="color: #333333; font-size: 18px; font-weight: 600; margin: 0 0 8px 0; line-height: 1.4;">
                {i}. {title}
            </h2>
            
            <div style="margin-bottom: 15px;">
                <span style="color: #888888; font-size: 13px; font-weight: 500;">
                    {date_str} | Source: {source}
                </span>
            </div>
            
            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0; text-align: justify;">
                {summary_text}
            </p>
            
            <p style="margin: 0;">
                <a href="{link}" style="background-color: #0066cc; color: white; padding: 8px 16px; text-decoration: none; font-size: 13px; font-weight: 500; border-radius: 4px; display: inline-block;">
                    Read Full Article
                </a>
            </p>
        </div>
        """
    
    # Create clean, professional email
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Technology News - {weekday}, {current_date}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; line-height: 1.6; color: #333333; background-color: #f8f9fa; margin: 0; padding: 20px;">
    
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        
        <!-- Header -->
        <div style="background-color: #ffffff; padding: 30px 30px 20px 30px; border-bottom: 2px solid #f0f0f0;">
            <h1 style="color: #2c3e50; font-size: 24px; font-weight: 700; margin: 0 0 8px 0; text-align: center;">
                AI Technology News
            </h1>
            <p style="color: #7f8c8d; font-size: 16px; margin: 0; text-align: center; font-weight: 500;">
                {weekday}, {current_date} • {len(articles)} Articles
            </p>
        </div>
        
        <!-- Articles -->
        <div style="padding: 30px;">
            {articles_html}
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px 30px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="color: #6c757d; font-size: 12px; margin: 0; line-height: 1.4;">
                AI-generated summaries • Delivered daily
            </p>
        </div>
        
    </div>
    
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
        import json
        start_time = datetime.utcnow()
        
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
                
                self.wfile.write(json.dumps(env_check).encode())
                return
            
            # Step 1: Fetch news articles with timeout protection
            try:
                print(f"[{datetime.utcnow().isoformat()}] Starting RSS feed fetch...")
                articles = fetch_news_articles()
                print(f"[{datetime.utcnow().isoformat()}] Found {len(articles) if articles else 0} articles")
            except Exception as e:
                print(f"RSS fetch error: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"RSS fetch failed: {str(e)}".encode())
                return
                
            if not articles:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"No articles found today.")
                return
            
            # Step 2: Generate AI summaries with timeout protection
            try:
                print(f"[{datetime.utcnow().isoformat()}] Starting AI summarization...")
                summarized_articles = summarize_with_gemini(articles)
                print(f"[{datetime.utcnow().isoformat()}] Generated {len(summarized_articles)} summaries")
            except Exception as e:
                print(f"AI summarization error: {e}")
                # Use articles without AI summaries as fallback
                summarized_articles = articles[:10]
                for article in summarized_articles:
                    article['ai_summary'] = create_detailed_fallback_summary(article)
            
            # Step 3: Send email with timeout protection
            try:
                print(f"[{datetime.utcnow().isoformat()}] Sending email...")
                send_daily_email(summarized_articles)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                success_msg = f"Success! Daily email sent with {len(summarized_articles)} articles in {execution_time:.1f}s at {datetime.utcnow().isoformat()}."
                print(success_msg)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(success_msg.encode())
                
            except Exception as e:
                error_msg = f"Failed to send daily email: {str(e)}"
                print(f"Email error: {error_msg}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(error_msg.encode())
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Handler error: {error_msg}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_msg.encode())
    
    def do_POST(self):
        self.do_GET()
