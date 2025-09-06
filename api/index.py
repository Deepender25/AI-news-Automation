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
    """Optimized RSS fetching with parallel processing for sub-30 second execution"""
    import socket
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    start_time = time.time()
    
    # Fast and reliable RSS feeds (6 sources for better coverage)
    RSS_FEEDS = [
        # Tier 1: Premium tech publications (fastest)
        "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://marktechpost.com/feed/",
        
        # Tier 2: Reliable and fast sources
        "https://research.google/blog/rss/",  # Google Research - usually fast
        "https://techcrunch.com/category/artificial-intelligence/feed/",  # TechCrunch AI
        "https://www.artificialintelligence-news.com/feed/"  # AI News - dedicated AI site
    ]
    
    def fetch_single_feed(url):
        """Fetch articles from single RSS feed with aggressive timeout"""
        articles = []
        original_timeout = socket.getdefaulttimeout()
        
        try:
            socket.setdefaulttimeout(3)  # 3-second timeout per feed
            feed = feedparser.parse(url)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                return articles
                
            today = datetime.utcnow().date()
            two_days_ago = today - timedelta(days=2)
            
            # Process only first 6 entries per feed for speed
            for entry in feed.entries[:6]:
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
                
                if article_date and article_date >= two_days_ago:
                    articles.append({
                        'title': getattr(entry, 'title', 'No Title'),
                        'link': getattr(entry, 'link', ''),
                        'summary': getattr(entry, 'summary', '')[:300],
                        'date': article_date,
                        'source': extract_domain(url)
                    })
                    
        except Exception as e:
            print(f"Error fetching feed {url}: {e}")
        finally:
            socket.setdefaulttimeout(original_timeout)
            
        return articles
    
    all_articles = []
    
    # Parallel RSS fetching with 15-second total timeout for 6 feeds
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_url = {executor.submit(fetch_single_feed, url): url for url in RSS_FEEDS}
            
            for future in as_completed(future_to_url, timeout=15):
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Feed fetch exception: {e}")
                    
    except Exception as e:
        print(f"Parallel fetch timeout or error: {e}")
    
    # Quick deduplication
    unique_articles = remove_duplicates(all_articles)
    
    fetch_time = time.time() - start_time
    print(f"RSS fetch completed in {fetch_time:.2f}s with {len(unique_articles)} articles")
    
    return unique_articles[:18]  # Limit to 18 articles for processing (6 feeds × 3 articles avg)

def extract_domain(url):
    """Extract clean, readable domain name from URL for source attribution"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Clean up domain name
        domain = domain.replace('www.', '').replace('feeds.', '').replace('feed.', '')
        
        # Create more readable source names (updated for 6 feeds)
        source_mapping = {
            'technologyreview.com': 'MIT Technology Review',
            'venturebeat.com': 'VentureBeat',
            'marktechpost.com': 'MarkTechPost',
            'research.google': 'Google Research',
            'techcrunch.com': 'TechCrunch',
            'artificialintelligence-news.com': 'AI News',
            # Legacy mappings (in case feeds change)
            'feedburner.com': 'AI News',
            'wired.com': 'Wired',
            'ai-techpark.com': 'AI TechPark',
            'bair.berkeley.edu': 'Berkeley AI Research',
            '404media.co': '404 Media'
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
    """Optimized AI summarization for sub-120 second execution"""
    import time
    
    start_time = time.time()
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not articles: 
        return []
    if not gemini_api_key: 
        return articles[:12]  # Return articles without AI summaries
    
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')  # Use Gemini 2.5 Flash for better quality
        
        # Process 10-12 articles for better coverage with 6 RSS feeds
        articles_to_process = articles[:12]
        summarized_articles = []
        
        print(f"Processing {len(articles_to_process)} articles with Gemini 2.5 Flash...")
        
        for i, article in enumerate(articles_to_process):
            try:
                # Simplified, faster prompt
                prompt = f"""Summarize this AI/tech article in 3-4 clear sentences. Focus on key facts and why it matters.

Title: {article['title']}
Source: {article['source']}
Content: {article.get('summary', '')[:300]}

Summary:"""
                
                response = model.generate_content(prompt)
                
                if response and response.text and response.text.strip():
                    ai_summary = response.text.strip()
                    if len(ai_summary) > 50:
                        enhanced_article = article.copy()
                        enhanced_article['ai_summary'] = ai_summary
                        summarized_articles.append(enhanced_article)
                        print(f"✅ {i+1}/12: {article['title'][:40]}...")
                        continue
                
                # Quick fallback
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
                summarized_articles.append(enhanced_article)
                
            except Exception as e:
                print(f"Error summarizing article {i+1}: {e}")
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
                summarized_articles.append(enhanced_article)
        
        ai_time = time.time() - start_time
        print(f"AI summarization completed in {ai_time:.2f}s for {len(summarized_articles)} articles")
        return summarized_articles
        
    except Exception as e:
        print(f"Gemini AI error: {e}")
        # Quick fallback articles
        fallback_articles = []
        for article in articles[:12]:
            enhanced_article = article.copy()
            enhanced_article['ai_summary'] = create_quick_fallback_summary(article)
            fallback_articles.append(enhanced_article)
        return fallback_articles

def create_quick_fallback_summary(article):
    """Create fast fallback summary for speed optimization"""
    title = article['title']
    original_summary = article.get('summary', '')
    source = article.get('source', 'Unknown Source')
    
    if original_summary and len(original_summary) > 50:
        # Use first 2 sentences of original summary
        sentences = original_summary.split('. ')[:2]
        summary_text = '. '.join(sentences) + '.'
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + '...'
    else:
        # Generate based on title
        summary_text = f"This article from {source} discusses developments in {title.lower()}. The announcement highlights ongoing innovation in artificial intelligence and technology."
    
    return summary_text

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
        import time
        
        # Performance monitoring
        start_time = time.time()
        step_times = {}
        
        try:
            # Check if this is a test endpoint
            if hasattr(self, 'path') and '/test' in self.path:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
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
            
            print(f"🚀 Starting optimized AI News automation at {datetime.utcnow().isoformat()}")
            print(f"🎯 Target execution time: <200 seconds")
            
            # Step 1: RSS Feed Processing
            step_start = time.time()
            try:
                print(f"📰 [STEP 1/3] Fetching RSS feeds...")
                articles = fetch_news_articles()
                step_times['rss_fetch'] = time.time() - step_start
                print(f"✅ RSS: {len(articles) if articles else 0} articles in {step_times['rss_fetch']:.1f}s")
            except Exception as e:
                step_times['rss_fetch'] = time.time() - step_start
                print(f"❌ RSS fetch failed in {step_times['rss_fetch']:.1f}s: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f"RSS fetch failed: {str(e)}".encode())
                return
                
            if not articles:
                total_time = time.time() - start_time
                print(f"❌ No articles found in {total_time:.1f}s")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b"No articles found today.")
                return
            
            # Step 2: AI Summarization
            step_start = time.time()
            try:
                print(f"🤖 [STEP 2/3] AI summarization ({len(articles)} articles)...")
                summarized_articles = summarize_with_gemini(articles)
                step_times['ai_processing'] = time.time() - step_start
                print(f"✅ AI: {len(summarized_articles)} summaries in {step_times['ai_processing']:.1f}s")
                    
            except Exception as e:
                step_times['ai_processing'] = time.time() - step_start
                print(f"⚠️ AI failed in {step_times['ai_processing']:.1f}s, using fallbacks: {e}")
                summarized_articles = articles[:12]
                for article in summarized_articles:
                    article['ai_summary'] = create_quick_fallback_summary(article)
            
            # Step 3: Email Delivery
            step_start = time.time()
            try:
                print(f"📧 [STEP 3/3] Sending email ({len(summarized_articles)} articles)...")
                send_daily_email(summarized_articles)
                step_times['email_send'] = time.time() - step_start
                
                # Performance Summary
                total_time = time.time() - start_time
                print(f"✅ Email sent in {step_times['email_send']:.1f}s")
                print(f"")
                print(f"📊 PERFORMANCE SUMMARY:")
                print(f"   RSS Fetch:     {step_times.get('rss_fetch', 0):.1f}s")
                print(f"   AI Processing: {step_times.get('ai_processing', 0):.1f}s")
                print(f"   Email Send:    {step_times.get('email_send', 0):.1f}s")
                print(f"   TOTAL TIME:    {total_time:.1f}s")
                
                # Performance analysis
                if total_time < 120:
                    print(f"🎯 EXCELLENT: Completed in {total_time:.1f}s (target: <200s)")
                elif total_time < 200:
                    print(f"✅ GOOD: Completed in {total_time:.1f}s (within target)")
                else:
                    print(f"⚠️ SLOW: Took {total_time:.1f}s (target: <200s)")
                
                success_msg = f"Success! Daily AI news sent ({len(summarized_articles)} articles) in {total_time:.1f}s at {datetime.utcnow().isoformat()}."
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(success_msg.encode())
                
            except Exception as e:
                step_times['email_send'] = time.time() - step_start
                total_time = time.time() - start_time
                error_msg = f"Email failed after {total_time:.1f}s: {str(e)}"
                print(f"❌ {error_msg}")
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
