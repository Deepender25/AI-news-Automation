#!/usr/bin/env python3
"""
Manual Email Sender - Send AI news email right now!
This script runs the email system locally to bypass Vercel authentication issues.
"""

import os
import sys
import feedparser
import google.generativeai as genai
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from datetime import datetime, timedelta
import re

# Add current directory to path to import our functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
    
    print("📡 Fetching AI news from RSS feeds...")
    
    for i, url in enumerate(RSS_FEEDS, 1):
        try:
            print(f"   [{i}/{len(RSS_FEEDS)}] {url.split('/')[2]}")
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
            print(f"   ⚠️ Error fetching {url}: {e}")
    
    # Remove duplicates based on title similarity
    unique_articles = remove_duplicates(all_articles)
    print(f"📊 Found {len(unique_articles)} unique articles from last 2 days")
    return unique_articles[:15]  # Limit for faster processing

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

def summarize_with_gemini(articles):
    """Create detailed AI summaries with bold key topics"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not articles: 
        return []
    if not gemini_api_key: 
        print("⚠️ GEMINI_API_KEY not found, using fallback summaries")
        # Return articles with detailed fallback summaries
        fallback_articles = []
        for article in articles:
            enhanced_article = article.copy()
            enhanced_article['ai_summary'] = create_detailed_fallback_summary(article)
            fallback_articles.append(enhanced_article)
        return fallback_articles
    
    try:
        print("🤖 Generating AI summaries with Gemini...")
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create individual summaries for each article
        summarized_articles = []
        
        # Process articles in smaller batches to avoid rate limits
        for i, article in enumerate(articles):
            try:
                print(f"   [{i+1}/{len(articles)}] Processing: {article['title'][:50]}...")
                
                # Add a small delay to avoid rate limiting
                if i > 0 and i % 3 == 0:
                    import time
                    time.sleep(1)  # 1-second pause every 3 articles
                
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
                        print(f"      ✅ AI summary generated")
                        continue
                
                # If AI summary failed, create a detailed fallback
                enhanced_article = article.copy()
                fallback_summary = create_detailed_fallback_summary(article)
                enhanced_article['ai_summary'] = fallback_summary
                summarized_articles.append(enhanced_article)
                print(f"      📝 Using fallback summary")
                
            except Exception as e:
                print(f"      ❌ Error summarizing article: {e}")
                # Add article with detailed fallback
                enhanced_article = article.copy()
                enhanced_article['ai_summary'] = create_detailed_fallback_summary(article)
                summarized_articles.append(enhanced_article)
        
        return summarized_articles
        
    except Exception as e:
        print(f"❌ Gemini AI error: {e}")
        # Return articles with detailed fallback summaries
        fallback_articles = []
        for article in articles:
            enhanced_article = article.copy()
            enhanced_article['ai_summary'] = create_detailed_fallback_summary(article)
            fallback_articles.append(enhanced_article)
        return fallback_articles

def create_daily_email(articles):
    """Create single professional email with all daily articles"""
    current_date = datetime.utcnow().strftime("%B %d, %Y")
    weekday = datetime.utcnow().strftime("%A")
    
    # Create articles HTML
    articles_html = ""
    
    for article in articles:
        summary_text = article.get('ai_summary', 'Visit the link below to read about this important development in AI and technology.')
        
        articles_html += f"""
        <div style="margin-bottom: 40px; padding-bottom: 30px; border-bottom: 1px solid #f0f0f0;">
            <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 20px; line-height: 1.4; font-weight: 700;">
                <a href="{article['link']}" style="color: #2c3e50; text-decoration: none;">{article['title']}</a>
            </h3>
            
            <p style="color: #7f8c8d; margin: 0 0 15px 0; font-size: 13px; font-weight: 500;">
                {current_date} | Source: {article['source'].replace('.com', '').replace('feedburner', 'AI News').title()}
            </p>
            
            <div style="margin-bottom: 20px;">
                <p style="color: #34495e; font-size: 15px; line-height: 1.7; margin: 0; text-align: justify;">{summary_text}</p>
            </div>
            
            <div style="margin-top: 15px;">
                <a href="{article['link']}" style="color: #3498db; text-decoration: none; font-size: 14px; font-weight: 600;">Read Full Article →</a>
            </div>
        </div>
"""
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Technology News - {current_date}</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333333; background-color: #ffffff; margin: 0; padding: 0;">
        <div style="max-width: 700px; margin: 0 auto; padding: 40px 30px; background-color: #ffffff;">
            
            <!-- Professional Header -->
            <div style="text-align: center; margin-bottom: 50px; padding-bottom: 30px; border-bottom: 3px solid #f0f0f0;">
                <h1 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">AI Technology News</h1>
                <p style="color: #7f8c8d; margin: 0; font-size: 16px; font-weight: 500;">{weekday}, {current_date}</p>
                <p style="color: #95a5a6; margin: 5px 0 0 0; font-size: 14px;">{len(articles)} articles • AI-summarized for your convenience</p>
            </div>
            
            <!-- Articles Content -->
            <div>
                {articles_html}
            </div>
            
            <!-- Professional Footer -->
            <div style="text-align: center; margin-top: 50px; padding-top: 30px; border-top: 2px solid #f0f0f0;">
                <p style="color: #95a5a6; font-size: 13px; margin: 0 0 10px 0; line-height: 1.6;">
                    Summaries generated by AI technology | Delivered manually for testing
                </p>
                <p style="color: #bdc3c7; font-size: 12px; margin: 0;">
                    <a href="https://ai-news-automation.vercel.app" style="color: #3498db; text-decoration: none;">AI News Automation Project</a>
                </p>
            </div>
            
        </div>
    </body>
    </html>
    """

def send_daily_email(articles):
    """Send single daily email with all articles"""
    print("📧 Preparing to send email...")
    
    brevo_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_emails_str = os.getenv("RECIPIENT_EMAILS")

    if not all([brevo_key, sender_email, recipient_emails_str]):
        missing = []
        if not brevo_key: missing.append("BREVO_API_KEY")
        if not sender_email: missing.append("SENDER_EMAIL")  
        if not recipient_emails_str: missing.append("RECIPIENT_EMAILS")
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    print(f"   📤 Sender: {sender_email}")
    print(f"   📥 Recipients: {recipient_emails_str}")

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
    subject = f"🤖 AI Technology News - {weekday}, {current_date} ({len(articles)} articles)"
    
    print(f"   📝 Subject: {subject}")

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=recipients,
        html_content=html_content,
        sender=sender,
        subject=subject
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print("   ✅ Email sent successfully!")
        return True
    except ApiException as e:
        print(f"   ❌ Brevo API Error: {e}")
        raise
    except Exception as e:
        print(f"   ❌ Email sending error: {e}")
        raise

def main():
    """Main function to run the manual email sender"""
    print("🚀 AI News Automation - Manual Email Sender")
    print("=" * 50)
    
    try:
        # Check environment variables first
        required_vars = ["BREVO_API_KEY", "SENDER_EMAIL", "RECIPIENT_EMAILS"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("\nPlease set these environment variables and try again.")
            return
        
        print("✅ Environment variables configured")
        
        # Fetch news articles
        articles = fetch_news_articles()
        if not articles:
            print("❌ No articles found today.")
            return
        
        # Generate AI summaries for each article
        summarized_articles = summarize_with_gemini(articles)
        
        # Send single daily email with all articles
        send_daily_email(summarized_articles)
        
        print("\n" + "=" * 50)
        print("🎉 SUCCESS! Check your inbox for the AI news digest!")
        print(f"📊 Sent {len(summarized_articles)} articles with detailed summaries")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return

if __name__ == "__main__":
    main()
