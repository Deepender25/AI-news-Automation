#!/usr/bin/env python3
"""Manual test script to trigger daily email"""

import requests
import time

# Stable production URL
VERCEL_URL = "https://ai-news-automation.vercel.app"

def test_email():
    print("🚀 Testing email system...")
    print(f"📡 Sending request to: {VERCEL_URL}")
    
    try:
        # Send request to trigger email
        response = requests.get(VERCEL_URL, timeout=60)
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📝 Response Content: {response.text}")
        
        if response.status_code == 200 and "Success!" in response.text:
            print("✅ Email sent successfully!")
            print("📧 Check your inbox for the AI news digest!")
        else:
            print("❌ Email sending failed")
            print(f"Error: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - the system might still be processing...")
        print("📧 Check your email in a few minutes")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email()
