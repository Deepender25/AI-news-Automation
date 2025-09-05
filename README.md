# AI News Automation

An automated system that fetches AI/tech news, summarizes it using Google's Gemini AI, and sends daily email briefings via Brevo (SendinBlue).

## ⚠️ Deployment Health Check

**Is your deployment not working? Start here!**

After deploying to Vercel, the most common issue is missing environment variables. We've created a health check endpoint to help you diagnose this.

Visit `https://<your-app-name>.vercel.app/api/check`

This will give you a real-time report on your configuration. If any variables are marked as "❌ Missing", you must add them in your Vercel project settings to get the application working.

---

## 🚀 Features

- **Comprehensive RSS Feed Scraping**: Fetches news from multiple high-quality AI and tech sources.
- **AI-Powered Summarization**: Uses Google Gemini to create concise, informative summaries.
- **Smart Content Filtering**: Filters for recent articles and removes duplicates.
- **Professional Email Design**: Delivers a clean, modern, and mobile-friendly HTML email.
- **Automated Daily Delivery**: Runs on a schedule using a GitHub Action.

## 📁 Project Structure

```
.
├── api/
│   ├── index.py        # Main automation logic
│   ├── check.py        # Health check and debugging endpoint
│   └── ...
├── .github/
│   └── workflows/
│       └── daily-news.yml # GitHub Action for scheduled runs
├── vercel.json         # Vercel deployment configuration
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## 🔧 Setup & Deployment

### 1. Get API Keys

You will need two free API keys:

- **Google Gemini API Key**: Get one from [Google AI Studio](https://makersuite.google.com/app/apikey).
- **Brevo (Sendinblue) API Key**: Sign up at [Brevo](https://www.brevo.com/) and create an API key.

### 2. Deploy to Vercel

The easiest way to deploy is by connecting your GitHub repository to Vercel.

1.  Push the code to your GitHub account.
2.  Create a new project on Vercel and import the repository.
3.  Vercel will automatically detect the configuration and deploy.

### 3. Set Environment Variables in Vercel

This is the most critical step. In your Vercel project dashboard, go to **Settings → Environment Variables** and add the following:

| Variable Name      | Description                        | Example                               |
| ------------------ | ---------------------------------- | ------------------------------------- |
| `GEMINI_API_KEY`   | Your Google AI Studio API key.     | `AIzaSy...`                           |
| `BREVO_API_KEY`    | Your Brevo (Sendinblue) API key.   | `xkeysib-...`                         |
| `SENDER_EMAIL`     | The email address to send from.    | `news@yourdomain.com`                 |
| `RECIPIENT_EMAILS` | Comma-separated list of recipients. | `user1@email.com,user2@email.com`     |

### 4. Verify Your Setup

After deployment, use the health check endpoint to confirm everything is configured correctly:

`https://<your-app-name>.vercel.app/api/check`

If it reports success, your application is ready!

## 📅 Scheduling

The daily job is scheduled to run via a GitHub Action, defined in `.github/workflows/daily-news.yml`. You can change the schedule by editing the `cron` property in that file.

Example:
```yaml
on:
  schedule:
    # Runs at 10:10 UTC daily
    - cron: '10 10 * * *'
```

## 🔍 Troubleshooting

If the health check at `/api/check` shows that all variables are set but the application still fails, consider the following:

- **Check Vercel Function Logs**: Go to the "Logs" tab in your Vercel project dashboard.
- **Check GitHub Action Logs**: Go to the "Actions" tab in your GitHub repository to see if the scheduled job ran successfully.
- **Invalid API Keys**: Ensure your API keys are correct and have the necessary permissions.
- **Test Email Sending**: Visit `/api/test-now` to send a simple test email. This can help isolate issues with your Brevo configuration.
