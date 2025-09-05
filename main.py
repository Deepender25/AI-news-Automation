#!/usr/bin/env python3
"""
AI News Automation - Railway Cron Job Version
Standalone script that fetches AI news, summarizes with Gemini, and sends daily emails.
"""

import os
import sys
import logging
from datetime import datetime
import traceback

# Import all the existing functions from the api module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.index import (
    fetch_news_articles,
    summarize_with_gemini,
    send_daily_email
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def validate_environment():
    """Validate all required environment variables are set"""
    required_vars = [
        'GEMINI_API_KEY',
        'BREVO_API_KEY', 
        'SENDER_EMAIL',
        'RECIPIENT_EMAILS'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ All environment variables are set")
    return True

def main():
    """Main execution function for the cron job"""
    start_time = datetime.utcnow()
    logger.info(f"🚀 Starting AI News Automation at {start_time.isoformat()}")
    
    try:
        # Step 1: Validate environment
        logger.info("🔍 Step 1: Validating environment variables...")
        if not validate_environment():
            logger.error("❌ Environment validation failed. Exiting.")
            sys.exit(1)
        
        # Step 2: Fetch news articles
        logger.info("📰 Step 2: Fetching AI news articles...")
        articles = fetch_news_articles()
        
        if not articles:
            logger.warning("⚠️  No articles found today. Exiting.")
            return
        
        logger.info(f"✅ Found {len(articles)} articles")
        
        # Step 3: Generate AI summaries
        logger.info("🤖 Step 3: Generating AI summaries with Gemini...")
        summarized_articles = summarize_with_gemini(articles)
        
        if not summarized_articles:
            logger.error("❌ No articles were successfully summarized. Exiting.")
            sys.exit(1)
        
        logger.info(f"✅ Successfully summarized {len(summarized_articles)} articles")
        
        # Step 4: Send daily email
        logger.info("📧 Step 4: Sending daily email...")
        try:
            send_daily_email(summarized_articles)
            logger.info("✅ Daily email sent successfully!")
            
        except Exception as email_error:
            logger.error(f"❌ Failed to send email: {str(email_error)}")
            raise email_error
        
        # Step 5: Log completion
        end_time = datetime.utcnow()
        duration = end_time - start_time
        logger.info(f"🎯 AI News Automation completed successfully!")
        logger.info(f"📊 Execution time: {duration.total_seconds():.2f} seconds")
        logger.info(f"📈 Articles processed: {len(summarized_articles)}")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main execution: {str(e)}")
        logger.error(f"📋 Stack trace: {traceback.format_exc()}")
        
        # Log the error details but don't fail silently
        end_time = datetime.utcnow()
        duration = end_time - start_time
        logger.error(f"⏱️ Failed after {duration.total_seconds():.2f} seconds")
        
        # Exit with error code so Railway knows it failed
        sys.exit(1)

if __name__ == "__main__":
    main()
