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
    """Fetch AI news from comprehensive RSS feed list - only today and yesterday articles"""
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
    yesterday = today - timedelta(days=1)  # Only today and yesterday
    
    # Set global socket timeout for RSS requests
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(4)  # Faster timeout for efficiency
    
    # Process more feeds but with faster timeouts to get 10-15 articles
    feeds_to_process = RSS_FEEDS[:6]  # Increased to 6 feeds for better coverage
    
    try:
        for url in feeds_to_process:
            try:
                # Parse feed with built-in timeout via socket setting
                feed = feedparser.parse(url)
                
                # Quick check if feed is valid
                if not hasattr(feed, 'entries') or not feed.entries:
                    continue
                    
                for entry in feed.entries[:15]:  # Check more entries per feed
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
                    
                    # Only include articles from today and yesterday
                    if article_date and article_date >= yesterday:
                        all_articles.append({
                            'title': getattr(entry, 'title', 'No Title'),
                            'link': getattr(entry, 'link', ''),
                            'summary': getattr(entry, 'summary', '')[:600],  # Slightly longer for better context
                            'date': article_date,
                            'source': extract_domain(url)
                        })
                        
                        # Stop early if we have enough articles for processing
                        if len(all_articles) >= 40:
                            break
                            
            except Exception as e:
                print(f"Error fetching feed {url}: {e}")
                continue  # Continue with next feed
                
            # Early exit if we have enough articles
            if len(all_articles) >= 40:
                break
                
    finally:
        # Restore original timeout
        socket.setdefaulttimeout(original_timeout)
    
    # Remove duplicates based on title similarity
    unique_articles = remove_duplicates(all_articles)
    print(f"Found {len(unique_articles)} unique articles from today and yesterday")
    return unique_articles

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
    """Create AI summaries for 10-15 interesting and knowledgeable articles"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not articles: 
        return []
    if not gemini_api_key: 
        return articles[:15]  # Return articles without AI summaries
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        # First, filter and rank articles by AI for interest and knowledge value
        print(f"Evaluating {len(articles)} articles for interest and knowledge...")
        
        # Step 1: Quick evaluation to select most interesting articles
        interesting_articles = []
        
        for i, article in enumerate(articles[:25]):  # Evaluate up to 25 articles
            try:
                # Quick evaluation prompt
                eval_prompt = f"""Rate this AI/tech article on a scale of 1-10 for:
1. How interesting/engaging it is for AI professionals
2. How much new knowledge or insights it provides
3. How significant the development/announcement is

Only respond with a number (1-10). Consider:
- Breaking news, major announcements = 8-10
- Significant research findings = 7-9  
- Industry insights, new tools = 6-8
- General updates, minor news = 4-6
- Repetitive or low-value content = 1-4

Title: {article['title']}
Source: {article['source']}
Content: {article.get('summary', '')[:400]}

Rating (1-10):"""
                
                response = model.generate_content(eval_prompt)
                
                if response and response.text and response.text.strip():
                    try:
                        rating = float(response.text.strip())
                        if rating >= 6.0:  # Only keep articles rated 6 or higher
                            article['ai_rating'] = rating
                            interesting_articles.append(article)
                            print(f"Article '{article['title'][:50]}...' rated {rating}")
                    except ValueError:
                        # If rating fails, include article anyway
                        article['ai_rating'] = 5.0
                        interesting_articles.append(article)
                
                # Small delay to avoid rate limiting
                if i > 0 and i % 5 == 0:
                    import time
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error evaluating article: {e}")
                # Include article if evaluation fails
                article['ai_rating'] = 5.0
                interesting_articles.append(article)
        
        # Sort by rating and take top 15
        interesting_articles.sort(key=lambda x: x.get('ai_rating', 0), reverse=True)
        selected_articles = interesting_articles[:15]
        
        # Ensure we have at least 10 articles
        if len(selected_articles) < 10 and len(articles) >= 10:
            # Add more articles to reach minimum 10
            remaining_articles = [a for a in articles if a not in selected_articles]
            selected_articles.extend(remaining_articles[:10-len(selected_articles)])
        
        print(f"Selected {len(selected_articles)} articles for detailed summarization")
        
        # Step 2: Create detailed summaries for selected articles
        summarized_articles = []
        
        for i, article in enumerate(selected_articles):
            try:
                # Enhanced prompt for better summaries
                prompt = f"""Create a comprehensive, informative summary (4-5 sentences) that provides readers with substantial knowledge about this AI/tech development.

REQUIREMENTS:
- Write 4-5 well-structured sentences
- Include specific details, numbers, company names, or technical aspects when available
- Explain the significance and potential impact
- Make it engaging and informative for AI professionals
- Use clear, professional language without markdown formatting
- Focus on what makes this development important or interesting

Title: {article['title']}
Source: {article['source']}
Date: {article['date']}
Original content: {article.get('summary', '')[:500]}

Create a detailed, knowledgeable summary:"""
                
                response = model.generate_content(prompt)
                
                if response and response.text and response.text.strip():
                    ai_summary = response.text.strip()
                    # Ensure we have a substantial summary
                    if len(ai_summary) > 150:
                        enhanced_article = article.copy()
                        enhanced_article['ai_summary'] = ai_summary
                        summarized_articles.append(enhanced_article)
                        print(f"✅ Summarized: {article['title'][:50]}...")
                        continue
                
                # If AI summary failed, create a detailed fallback
                print(f"⚠️ AI summary failed for: {article['title'][:50]}...")
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
            
            # Small delay between summaries
            if i > 0 and i % 3 == 0:
                import time
                time.sleep(0.3)
        
        print(f"Completed summarization of {len(summarized_articles)} articles")
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
    """Create a comprehensive fallback summary when AI fails"""
    title = article['title']
    original_summary = article.get('summary', '')
    source = article.get('source', 'Unknown Source')
    
    if original_summary and len(original_summary) > 100:
        # Clean and use the original summary
        # Remove HTML tags if present
        import re
        clean_summary = re.sub(r'<[^>]+>', '', original_summary)
        
        # Split into sentences and take the most informative ones
        sentences = clean_summary.split('. ')
        if len(sentences) >= 4:
            summary_text = '. '.join(sentences[:4]) + '.'
        elif len(sentences) >= 2:
            summary_text = '. '.join(sentences[:2]) + '.'
        else:
            summary_text = clean_summary[:400] + '...' if len(clean_summary) > 400 else clean_summary
        
        # Ensure it ends properly
        if not summary_text.endswith('.'):
            summary_text += '.'
            
        return f"{summary_text} This development from {source} represents significant progress in artificial intelligence and technology, highlighting the ongoing innovation that continues to shape the industry landscape."
    else:
        # Create a more detailed summary based on title analysis
        title_lower = title.lower()
        
        # Try to extract key topics from title
        if any(word in title_lower for word in ['breakthrough', 'announces', 'launches', 'releases']):
            context = "This major announcement"
        elif any(word in title_lower for word in ['research', 'study', 'findings']):
            context = "This research development"
        elif any(word in title_lower for word in ['model', 'ai', 'algorithm']):
            context = "This AI advancement"
        else:
            context = "This technology development"
            
        return f"{context} focuses on {title.lower()}. The article from {source} covers important innovations and insights in the artificial intelligence sector. This advancement demonstrates the rapid pace of AI development and its growing impact across various industries. The development represents another step forward in the evolution of artificial intelligence technology."

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
                print(f"[{datetime.utcnow().isoformat()}] Found {len(articles) if articles else 0} articles from today/yesterday")
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
                self.wfile.write(b"No articles found from today or yesterday.")
                return
            
            # Ensure we have enough articles for processing
            if len(articles) < 5:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"Only {len(articles)} articles found - need at least 5 for processing.".encode())
                return
            
            # Step 2: Generate AI summaries with timeout protection
            try:
                print(f"[{datetime.utcnow().isoformat()}] Starting AI evaluation and summarization...")
                summarized_articles = summarize_with_gemini(articles)
                print(f"[{datetime.utcnow().isoformat()}] Generated {len(summarized_articles)} high-quality summaries")
                
                # Ensure we have 10-15 articles as requested
                if len(summarized_articles) < 10:
                    print(f"Warning: Only {len(summarized_articles)} articles processed, target was 10-15")
                elif len(summarized_articles) > 15:
                    summarized_articles = summarized_articles[:15]
                    print(f"Trimmed to 15 articles as requested")
                    
            except Exception as e:
                print(f"AI summarization error: {e}")
                # Use articles without AI summaries as fallback
                summarized_articles = articles[:12]  # Take 12 for middle ground
                for article in summarized_articles:
                    article['ai_summary'] = create_detailed_fallback_summary(article)
                print(f"Using fallback summaries for {len(summarized_articles)} articles")
            
            # Step 3: Send email with timeout protection
            try:
                print(f"[{datetime.utcnow().isoformat()}] Sending email...")
                send_daily_email(summarized_articles)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                success_msg = f"Success! Daily email sent with {len(summarized_articles)} high-quality AI articles (today/yesterday only) in {execution_time:.1f}s at {datetime.utcnow().isoformat()}."
                print(success_msg)
                
                # Log performance metrics
                if execution_time > 200:
                    print(f"⚠️ Warning: Execution took {execution_time:.1f}s (target: <200s)")
                else:
                    print(f"✅ Performance: Completed within target time ({execution_time:.1f}s < 200s)")
                
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
