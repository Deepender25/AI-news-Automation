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
                
                # Create detailed prompt for comprehensive summary
                prompt = f"""Create a comprehensive, detailed summary (8-10 lines) of this AI/Tech news article. 
Make it informative enough that readers can understand the full story without clicking the link.

FORMATTING RULES:
- Use **bold** for company names (OpenAI, Google, Microsoft, etc.)
- Use **bold** for AI model names (GPT-4, Claude, Gemini, etc.)
- Use **bold** for product names (ChatGPT, Copilot, Bard, etc.)
- Use **bold** for key technical terms and concepts
- DO NOT use quotes - just bold formatting
- Write in clear, professional language
- Include specific details, numbers, and context
- Explain the significance and implications

Title: {article['title']}
Source: {article['source']}
Original Content: {article['summary'][:600] if article['summary'] else 'Limited content available'}

Provide a detailed, comprehensive summary that covers all key points:"""
                
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
    """Create single professional email with perfect consistent formatting"""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    
    # Create articles HTML with perfect consistency
    articles_html = ""
    
    for i, article in enumerate(articles, 1):
        # Clean and format article data
        title = article.get('title', 'Untitled Article').strip()
        link = article.get('link', '#').strip()
        source = article.get('source', 'Unknown').replace('.com', '').replace('feedburner', 'AI News').replace('www.', '').title()
        
        # Get AI summary, ensure it exists and is properly formatted
        summary_text = article.get('ai_summary', '')
        if not summary_text:
            summary_text = "This article discusses important developments in artificial intelligence and technology. The advancement represents significant progress in the AI sector with potential implications for businesses and users."
        
        # Clean summary text for HTML
        summary_text = summary_text.replace('\n', '</p><p style="color: #34495e; font-size: 15px; line-height: 1.8; margin: 12px 0; text-align: justify;">')
        
        articles_html += f"""
            <article style="margin-bottom: 45px; padding-bottom: 35px; border-bottom: 1px solid #e8ecf0;">
                <!-- Article Header -->
                <header>
                    <h2 style="color: #2c3e50; margin: 0 0 12px 0; font-size: 22px; line-height: 1.3; font-weight: 600; letter-spacing: -0.3px;">
                        <a href="{link}" style="color: #2c3e50; text-decoration: none; hover: text-decoration: underline;">
                            {title}
                        </a>
                    </h2>
                    
                    <div style="margin-bottom: 20px;">
                        <span style="color: #7f8c8d; font-size: 13px; font-weight: 500;">
                            📅 {current_date}
                        </span>
                        <span style="color: #bdc3c7; margin: 0 8px; font-size: 13px;">•</span>
                        <span style="color: #7f8c8d; font-size: 13px; font-weight: 500;">
                            📰 {source}
                        </span>
                    </div>
                </header>
                
                <!-- Article Summary -->
                <div style="margin-bottom: 25px;">
                    <p style="color: #34495e; font-size: 15px; line-height: 1.8; margin: 12px 0; text-align: justify;">
                        {summary_text}
                    </p>
                </div>
                
                <!-- Read More Link -->
                <footer>
                    <a href="{link}" style="display: inline-block; background-color: #3498db; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-size: 14px; font-weight: 600; transition: background-color 0.3s ease;">
                        Read Full Article →
                    </a>
                </footer>
            </article>
        """
    
    # Create perfect HTML email structure
    return f"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="x-apple-disable-message-reformatting">
    <title>🤖 AI Technology News - {current_date}</title>
    <style type="text/css">
        /* Email Client Compatibility */
        body, table, td, a {{ color: inherit; text-decoration: none; }}
        .email-container {{ max-width: 680px; margin: 0 auto; }}
        .article-link:hover {{ background-color: #2980b9 !important; }}
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {{
            .email-body {{ background-color: #1a1a1a !important; color: #ffffff !important; }}
            .email-container {{ background-color: #2d2d2d !important; }}
        }}
        
        /* Mobile responsiveness */
        @media screen and (max-width: 600px) {{
            .email-container {{ width: 100% !important; padding: 20px !important; }}
            .article-title {{ font-size: 20px !important; }}
            .article-summary {{ font-size: 14px !important; }}
        }}
    </style>
</head>
<body class="email-body" style="margin: 0; padding: 0; background-color: #f7f9fc; font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">
    
    <!-- Email Container -->
    <div class="email-container" style="max-width: 680px; margin: 0 auto; background-color: #ffffff;">
        
        <!-- Header Section -->
        <header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; color: white;">
            <h1 style="margin: 0 0 8px 0; font-size: 32px; font-weight: 700; letter-spacing: -0.5px;">
                🤖 AI Technology News
            </h1>
            <p style="margin: 0 0 5px 0; font-size: 18px; font-weight: 400; opacity: 0.9;">
                {weekday}, {current_date}
            </p>
            <p style="margin: 0; font-size: 14px; opacity: 0.8;">
                {len(articles)} articles • AI-curated & summarized
            </p>
        </header>
        
        <!-- Main Content -->
        <main style="padding: 40px 30px;">
            
            <!-- Welcome Message -->
            <div style="text-align: center; margin-bottom: 40px; padding: 20px; background-color: #f8f9ff; border-radius: 8px; border-left: 4px solid #3498db;">
                <p style="color: #2c3e50; font-size: 16px; margin: 0; line-height: 1.6;">
                    📡 <strong>Latest AI & Technology News</strong> with detailed summaries generated by artificial intelligence
                </p>
            </div>
            
            <!-- Articles Section -->
            <section>
                {articles_html}
            </section>
            
        </main>
        
        <!-- Footer Section -->
        <footer style="background-color: #2c3e50; padding: 30px; text-align: center; color: #ecf0f1;">
            <div style="margin-bottom: 15px;">
                <p style="margin: 0; font-size: 14px; line-height: 1.6;">
                    ⚡ Powered by <strong>Gemini AI</strong> | 🕒 Delivered daily at 11:55 PM UTC
                </p>
            </div>
            
            <div style="margin-bottom: 15px;">
                <a href="https://ai-news-automation.vercel.app" style="color: #3498db; text-decoration: none; font-weight: 500;">
                    🔧 AI News Automation System
                </a>
            </div>
            
            <div style="border-top: 1px solid #34495e; padding-top: 15px; margin-top: 15px;">
                <p style="margin: 0; font-size: 12px; color: #95a5a6; line-height: 1.5;">
                    This email contains AI-generated summaries of technology news articles.<br>
                    Articles are sourced from trusted technology publications and summarized for your convenience.
                </p>
            </div>
        </footer>
        
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
