# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

AI News Automation is a streamlined news aggregation system that fetches AI/technology news from RSS feeds, summarizes articles using Google Gemini AI, and sends formatted email briefings. The system runs on Vercel serverless functions and is triggered by EasyCron for reliable daily scheduling.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Note: This is a serverless application - functions run in Vercel environment
# For local testing, use the deployed endpoints
```

### Testing & Debugging
```bash
# Test the health check endpoint
Invoke-WebRequest -Uri "https://your-deployment.vercel.app/api/check"

# Trigger manual news automation
Invoke-WebRequest -Uri "https://your-deployment.vercel.app/api/index"

# Test simple endpoint availability
Invoke-WebRequest -Uri "https://your-deployment.vercel.app/api/simple"
```

### Deployment Commands
```bash
# Deploy to Vercel (requires Vercel CLI)
vercel deploy

# Or connect GitHub repo to Vercel for automatic deployments
```

## Architecture Overview

The system operates as a simple, reliable serverless application:

### Core Components

**RSS Feed Processing (`api/index.py`)**
- Fetches from 10+ AI/tech RSS feeds with timeout handling
- Processes articles from last 3 days, deduplicates by title similarity
- Limits to 5 feeds and 30 articles to avoid timeout issues
- Extracts clean source names and formats article metadata

**AI Summarization Pipeline**
- Uses Google Gemini 2.5 Pro for article summarization
- Implements rate limiting (1-second delays every 8 requests)
- Creates 3-4 sentence informative summaries
- Falls back to content-based summaries when AI fails
- Processes up to 15 articles to ensure 10+ quality summaries

**Email Generation & Delivery**
- Creates professional HTML emails with article numbering
- Uses Brevo (SendinBlue) for transactional email delivery
- Supports multiple recipients via comma-separated environment variable
- Includes responsive design with clean typography and branding

### Deployment Architecture

**Vercel Serverless Functions**
- API routes in `api/` directory handle HTTP requests
- `api/index.py` - Main automation endpoint (fetches news, generates summaries, sends email)
- `api/check.py` - Environment variable health check and diagnostics
- `api/simple.py` - Basic availability and uptime check
- Triggered via cron-job.org HTTP requests at scheduled times
- 5-minute (300-second) timeout limit per function execution

**External Scheduling**
- EasyCron makes HTTP GET request to `/api/index` daily at 11:59 PM IST
- Reliable timing with longer timeout handling than many alternatives
- Free tier with 2 cron jobs available
- Web-based interface with execution history and monitoring
- Better timeout handling for longer-running functions

## Key Technical Patterns

### Error Handling Strategy
- RSS feed failures don't stop processing (continue with next feed)
- AI summarization failures fall back to content-based summaries
- Email delivery failures propagate as fatal errors
- Comprehensive logging with emoji-based status indicators

### Performance Optimizations
- Socket-level timeouts (8 seconds per RSS feed)
- Limited concurrent AI requests to avoid rate limiting
- Early termination when sufficient articles are collected
- Content length limits to prevent oversized emails

### Environment Configuration
Required variables for both deployment modes:
- `GEMINI_API_KEY` - Google AI Studio API key
- `BREVO_API_KEY` - Brevo (SendinBlue) transactional email key  
- `SENDER_EMAIL` - Verified sender email address
- `RECIPIENT_EMAILS` - Comma-separated list of recipient addresses

## Development Guidelines

### Adding New RSS Feeds
Modify the `RSS_FEEDS` array in `api/index.py` and update the `source_mapping` dictionary with readable source names. Test feed reliability before adding to production.

### Modifying AI Prompts
Update the prompt in `summarize_with_gemini()` function. Maintain the requirement for 3-4 sentence summaries to preserve email formatting consistency.

### Email Template Changes
Edit the `create_daily_email()` function for visual modifications. Maintain responsive design principles and test across email clients.

### Scheduling Adjustments
- **EasyCron**: Modify schedule in the web dashboard
- Uses standard cron syntax (e.g., `29 18 * * *` for 6:29 PM UTC / 11:59 PM IST daily)
- Current schedule: Daily at 11:59 PM IST
- Web interface supports easy schedule modification and testing

## Troubleshooting Common Issues

### No Articles in Email
- RSS feeds may be temporarily unavailable
- Date filtering might be too restrictive (articles older than 3 days)
- Check RSS feed URLs for changes or deprecation

### AI Summarization Failures
- Verify Gemini API key and quota limits
- Rate limiting may require longer delays between requests
- Fallback summaries will be used automatically

### Email Delivery Issues
- Verify Brevo API key and sender email domain verification
- Check recipient email format (comma-separated, no spaces)
- Review Brevo dashboard for delivery logs and bounces

### Deployment-Specific Issues
- **Vercel**: Environment variables must be set in project dashboard
- **EasyCron**: Check execution history and logs for failed requests
- **Timeout Issues**: EasyCron may report timeouts while Vercel function succeeds
- **Success Indicator**: If email is received, automation worked despite HTTP timeout
- **Processing Time**: Function typically takes 2-4 minutes; Vercel allows up to 5 minutes

## File Structure Context

- `api/` - Vercel serverless functions (HTTP handlers)
  - `index.py` - Main automation logic
  - `check.py` - Health check and diagnostics
  - `simple.py` - Basic availability check
- `vercel.json` - Vercel deployment configuration
- `requirements.txt` - Python dependencies
- `WARP.md` - Development guidance (this file)
- `README.md` - Project documentation
