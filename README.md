# AI News Automation

An automated system that fetches AI/tech news, summarizes it using Google's Gemini AI, and sends daily email briefings via Brevo (SendinBlue).

## 🚀 Features

- **Comprehensive RSS Feed Scraping**: Fetches AI/tech news from 12+ premium sources:
  - MIT Technology Review, VentureBeat AI, WIRED AI
  - MarkTechPost, AI Tech Park, KnowTechie
  - Google Research Blog, Berkeley AI Research
  - Sebastian Raschka's AI Magazine, and more
- **Smart Content Filtering**: Only shows articles from today and yesterday
- **Duplicate Removal**: Intelligent deduplication based on title similarity
- **AI-Powered Summarization**: Google Gemini AI creates executive summaries
- **Professional Email Design**: Beautiful HTML template with modern styling
- **Source Attribution**: Articles grouped by source with direct links
- **Automated Daily Delivery**: Runs at 11:55 PM UTC via Vercel cron jobs
- **Scalable Architecture**: Handles 50+ articles from multiple sources

## 📁 Project Structure

```
ai_news_automation/
├── api/
│   ├── index.py        # Main automation logic
│   ├── simple.py       # Simple status endpoint
│   └── test-now.py     # Email testing endpoint
├── vercel.json         # Vercel deployment config
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🔧 Setup & Deployment

### 1. Get Required API Keys

**Google Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Save it as `GEMINI_API_KEY`

**Brevo API Key:**
1. Sign up at [Brevo](https://www.brevo.com/)
2. Go to SMTP & API → API Keys
3. Create a new API key
4. Save it as `BREVO_API_KEY`

### 2. Deploy to Vercel

#### Option A: Using Vercel CLI
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

#### Option B: Using GitHub Integration
1. Push code to GitHub repository
2. Connect repository to Vercel
3. Deploy automatically

### 3. Set Environment Variables in Vercel

In your Vercel dashboard → Settings → Environment Variables, add:

| Variable | Value | Example |
|----------|-------|---------|
| `GEMINI_API_KEY` | Your Google AI Studio API key | `AIzaSy...` |
| `BREVO_API_KEY` | Your Brevo API key | `xkeysib-...` |
| `SENDER_EMAIL` | Email address to send from | `news@yourdomain.com` |
| `RECIPIENT_EMAILS` | Comma-separated recipient emails | `user1@email.com,user2@email.com` |

### 4. Test the Deployment

After deployment, test your endpoints:

- **Main endpoint**: `https://your-app.vercel.app/api/index`
- **Test endpoint**: `https://your-app.vercel.app/api/test-now`
- **Status endpoint**: `https://your-app.vercel.app/api/simple`

## 📅 Scheduling

The cron job runs daily at **11:55 PM UTC** (configured in `vercel.json`). To change the schedule:

```json
{
  "crons": [
    {
      "path": "/api/index",
      "schedule": "0 9 * * *"  // 9:00 AM UTC daily
    }
  ]
}
```

## 🧪 Testing

### Test Email Functionality
Visit: `https://your-app.vercel.app/api/test-now`

This will send a test email to verify your configuration.

### Manual Trigger
Visit: `https://your-app.vercel.app/api/index`

This will run the full news automation process immediately.

## 📧 Email Format

The system sends HTML-formatted emails with:
- Subject: "Your Daily AI, ML & Tech Briefing 🚀"
- Clean HTML formatting with headers and bullet points
- Fallback content if AI summarization fails

## 🔍 Troubleshooting

### Common Issues:

1. **"GEMINI_API_KEY not found"**
   - Verify the environment variable is set in Vercel
   - Check the API key is valid in Google AI Studio

2. **"Email environment variables not fully set"**
   - Ensure all email variables are set: `BREVO_API_KEY`, `SENDER_EMAIL`, `RECIPIENT_EMAILS`

3. **"Error fetching feed"**
   - RSS feeds might be temporarily unavailable
   - The system will continue with available feeds

4. **Cron job not running**
   - Cron jobs require a Vercel Pro plan
   - Check Vercel Functions logs for errors

### Debugging:
- Check Vercel Function logs in your dashboard
- Test individual endpoints manually
- Use the `/api/test-now` endpoint to verify email setup

## 💡 Customization

### Adding More RSS Feeds:
Edit the `RSS_FEEDS` list in `api/index.py`:

```python
RSS_FEEDS = [
    "https://marktechpost.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/tag/artificial-intelligence/feed/",
    "https://your-custom-feed.com/feed/",  # Add your feed here
]
```

### Changing Email Subject/Content:
Modify the email parameters in the `send_email_with_brevo()` function.

### Adjusting News Count:
Change the slice parameters in `fetch_news_articles()`:
- `RSS_FEEDS[:2]` - Number of feeds to process
- `feed.entries[:3]` - Number of articles per feed

## 📜 License

Open source - feel free to modify and use for your projects!
