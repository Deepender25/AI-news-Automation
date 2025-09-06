# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

AI News Automation is an optimized news aggregation system that fetches AI/technology news from RSS feeds, summarizes articles using Google Gemini AI, and sends formatted email briefings. The system runs on Vercel serverless functions with GitHub Actions scheduling, optimized for sub-200 second execution.

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

The system operates as an optimized serverless application designed for speed and reliability:

### Core Components

**Parallel RSS Feed Processing (`api/index.py`)**
- Processes 3 fastest RSS feeds concurrently with ThreadPoolExecutor
- 3-second timeout per feed, 10-second total RSS processing timeout
- Fetches articles from last 2 days only for relevance
- Limits to 6 entries per feed for speed optimization

**Fast AI Summarization Pipeline**
- Uses Google Gemini 1.5 Flash for faster response times
- Processes maximum 8 articles to stay within time limits
- Simplified prompt structure for quicker AI responses
- Quick fallback summaries when AI processing is slow

**Email Generation & Delivery**
- Creates professional HTML emails with responsive design
- Uses Brevo (SendinBlue) for reliable transactional email delivery
- Includes performance metrics in success messages
- Supports multiple recipients via comma-separated environment variable

### Deployment Architecture

**Vercel Serverless Functions**
- API routes in `api/` directory handle HTTP requests
- `api/index.py` - Main automation endpoint (RSS → AI → Email)
- `api/check.py` - Environment variable health check and diagnostics
- `api/simple.py` - Basic availability and uptime check
- 5-minute (300-second) timeout limit per function execution
- Real-time performance monitoring with step-by-step timing

**GitHub Actions Scheduling**
- Automated daily execution at 11:30 PM IST (6:00 PM UTC)
- Built-in retry logic and error handling
- Free with GitHub repository (no external dependencies)
- Comprehensive execution logs and performance monitoring
- 15-minute timeout with 5-minute Vercel function limit

## Key Technical Patterns

### Performance Optimizations (Target: <200s)
- **Parallel RSS Processing**: 3 feeds processed concurrently with 3s timeout each
- **Fast AI Model**: Uses Gemini 1.5 Flash instead of 2.5 Pro for speed
- **Limited Article Processing**: Maximum 8 articles to reduce AI processing time
- **Step-by-Step Monitoring**: Real-time performance tracking for each phase
- **Quick Fallbacks**: Fast summary generation when AI processing fails

### Error Handling Strategy
- RSS feed failures don't stop processing (parallel execution continues)
- AI summarization failures use quick fallback summaries
- Email delivery failures propagate as fatal errors
- Comprehensive performance logging with timing breakdowns

### Environment Configuration
Required variables for both deployment modes:
- `GEMINI_API_KEY` - Google AI Studio API key
- `BREVO_API_KEY` - Brevo (SendinBlue) transactional email key  
- `SENDER_EMAIL` - Verified sender email address
- `RECIPIENT_EMAILS` - Comma-separated list of recipient addresses

## Development Guidelines

### Performance Monitoring
The system includes comprehensive performance tracking:
- RSS fetch timing (target: <30 seconds)
- AI processing timing (target: <120 seconds) 
- Email delivery timing (target: <10 seconds)
- Total execution time (target: <200 seconds)

### Adding New RSS Feeds
Modify the `RSS_FEEDS` array in `api/index.py`. Note that only the 3 fastest feeds are processed to maintain performance targets. Test feed reliability and response times before adding.

### Modifying AI Processing
- Keep article count at 8 or below to maintain speed
- Use Gemini 1.5 Flash model for faster responses
- Maintain simple prompt structures for quick processing
- Always include fallback summary generation

### Email Template Changes
Edit the `create_daily_email()` function for visual modifications. Maintain responsive design principles and test across email clients.

### Scheduling Adjustments
- **GitHub Actions**: Modify cron schedule in `.github/workflows/daily-ai-news.yml`
- Uses standard cron syntax (currently `0 18 * * *` for 6:00 PM UTC / 11:30 PM IST daily)
- Current schedule: Daily at 11:30 PM IST
- Supports manual triggers via workflow_dispatch for testing

## Troubleshooting Common Issues

### Performance Issues
- Check step-by-step timing logs in Vercel function logs
- RSS fetch should complete in <30 seconds
- AI processing should complete in <120 seconds
- Total execution should be <200 seconds

### No Articles in Email
- RSS feeds may be temporarily unavailable (check parallel processing logs)
- Date filtering limits to last 2 days only
- Check RSS feed URLs for changes or deprecation

### AI Summarization Failures
- Verify Gemini API key and quota limits
- System automatically falls back to quick summaries
- Check if using correct model (Gemini 1.5 Flash)

### Email Delivery Issues
- Verify Brevo API key and sender email domain verification
- Check recipient email format (comma-separated, no spaces)
- Review Brevo dashboard for delivery logs and bounces

### Deployment-Specific Issues
- **Vercel**: Environment variables must be set in project dashboard
- **GitHub Actions**: Check execution history in repository's Actions tab
- **Performance Issues**: Monitor step-by-step timing in function logs
- **Target Performance**: Function should complete in under 200 seconds
- **Success Indicator**: Check both GitHub Actions status and email delivery
- **Timeout Handling**: GitHub Actions has 15-minute timeout, Vercel functions timeout at 5 minutes

## File Structure Context

- `api/` - Vercel serverless functions (HTTP handlers)
  - `index.py` - Main automation logic with performance optimization
  - `check.py` - Health check and diagnostics
  - `simple.py` - Basic availability check
- `.github/workflows/daily-ai-news.yml` - GitHub Actions automation workflow
- `vercel.json` - Vercel deployment configuration (5-minute timeout)
- `requirements.txt` - Python dependencies
- `WARP.md` - Development guidance (this file)
- `README.md` - Project documentation

## Performance Expectations

### Target Execution Times
- RSS Processing: 15-30 seconds (parallel execution)
- AI Summarization: 60-120 seconds (8 articles max)
- Email Generation: 5-10 seconds
- **Total Target: Under 200 seconds**

### Success Indicators
- GitHub Actions workflow completes successfully
- Email delivery confirmed via Brevo
- Performance logs show sub-200 second execution
- All processing steps complete without timeouts
