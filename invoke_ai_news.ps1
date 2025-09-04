# AI News Automation - Manual Invoke Script
# Calls the stable URL to trigger daily email

Write-Host "🚀 Invoking AI News Automation..." -ForegroundColor Green
Write-Host "📡 URL: https://ai-news-automation.vercel.app" -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "https://ai-news-automation.vercel.app" -Method GET -TimeoutSec 300 -UseBasicParsing
    
    Write-Host "📊 Response Status: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "📝 Response Content:" -ForegroundColor Yellow
    Write-Host $response.Content
    
    if ($response.StatusCode -eq 200 -and $response.Content -like "*Success*") {
        Write-Host "✅ Email sent successfully!" -ForegroundColor Green
        Write-Host "📧 Check your inbox for the AI news digest!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Check response above for details" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Note: If you see authentication error, open https://ai-news-automation.vercel.app in your browser first" -ForegroundColor Cyan
}
