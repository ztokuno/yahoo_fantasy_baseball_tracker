# Yahoo Fantasy Sports API Setup Guide

## Overview
This guide will walk you through setting up API credentials to access Yahoo Fantasy Sports data for your baseball stat tracker project.

## Step 1: Create a Yahoo Developer Account

1. Go to the [Yahoo Developer Network](https://developer.yahoo.com/)
2. Sign in with your Yahoo account (the same one you use for Fantasy Baseball)
3. If prompted, agree to the Terms of Service

## Step 2: Create a New App

1. Navigate to **My Apps** in the Yahoo Developer dashboard
2. Click **Create an App** button
3. Fill out the application form:

### Application Details:
- **Application Name**: Something descriptive like "Fantasy Baseball Stat Tracker"
- **Application Type**: Select **Web Application**
- **Description**: Brief description of your project (e.g., "Personal fantasy baseball statistics tracker and recap generator")
- **Home Page URL**: You can use `http://localhost:8000` for local development
- **Redirect URI(s)**: This is important! Use `https://localhost:8000/callback` or `oob` (out-of-band)
  - For most personal projects, using `oob` is simplest as it doesn't require setting up a callback server
  - Add this exact value: `oob`
- **API Permissions**: Select **Fantasy Sports** and make sure **Read** is checked

4. Click **Create App**

## Step 3: Get Your Credentials

After creating your app, you'll be taken to your app's page where you'll see:

- **Client ID (Consumer Key)**: A long string of characters - this is your app's public identifier
- **Client Secret (Consumer Secret)**: Another long string - keep this private!

**Important**: Copy both of these and save them securely. You'll need them for authentication.

## Step 4: Set Up Your Credentials File

For security, you should store these credentials in a separate file that you **don't commit to version control**.

Create a file called `credentials.json` in your project directory:

```json
{
  "consumer_key": "YOUR_CLIENT_ID_HERE",
  "consumer_secret": "YOUR_CLIENT_SECRET_HERE"
}
```

**Security Best Practice**: Add `credentials.json` to your `.gitignore` file if you're using git:

```bash
# In your project root
echo "credentials.json" >> .gitignore
```

## Step 5: Understanding OAuth Flow

Yahoo uses OAuth 2.0 for authentication. Here's what happens:

1. Your app requests authorization from Yahoo
2. You (the user) approve the request through a browser
3. Yahoo provides an authorization code
4. Your app exchanges this code for an access token
5. The access token is used for all API requests

### First-Time Authorization:
- You'll need to manually authorize your app the first time
- Yahoo will provide a verification code
- Your script will exchange this for access and refresh tokens

### Subsequent Uses:
- Your app will use a refresh token to get new access tokens
- Access tokens expire after about 1 hour
- Refresh tokens are valid for longer and can be stored for future use

## Step 6: Test Your Setup

Once you have your credentials, you can test the connection. Here's a simple test script:

```python
import json
from yahoo_oauth import OAuth2

# Load credentials
with open('credentials.json', 'r') as f:
    creds = json.load(f)

# Initialize OAuth - this will open a browser for first-time auth
oauth = OAuth2(None, None, from_file='oauth2.json')

# If successful, you'll see oauth2.json created with your tokens
print("Authentication successful!")
```

## Step 7: Install Required Python Package

```bash
pip install yahoo_oauth
```

Or if you prefer the yahoo-fantasy-api wrapper (recommended):

```bash
pip install yahoo_fantasy_api
```

## Troubleshooting

### "Invalid redirect URI"
- Make sure your redirect URI in the Yahoo app settings matches exactly what you're using in your code
- For command-line apps, use `oob`

### "Invalid client credentials"
- Double-check your consumer key and secret
- Make sure there are no extra spaces or quotes copied

### Authentication opens browser but fails
- Check that you're logged into the correct Yahoo account
- Clear your browser cookies for Yahoo and try again
- Make sure your Yahoo account has access to the fantasy league you're trying to query

### "Invalid grant" errors
- Your refresh token may have expired
- Delete the `oauth2.json` file and re-authenticate

## Next Steps

Once you have your credentials set up and tested:

1. You can start making API calls to retrieve league data
2. Set up a scheduled job to run your data collection script
3. Build out your stat tracking and recap generation features

## Important Notes

- **Rate Limits**: Yahoo has rate limits on API calls (typically around 10,000 requests per day for authenticated apps)
- **Token Storage**: The `oauth2.json` file contains sensitive tokens - add it to `.gitignore`
- **Credential Security**: Never share or commit your consumer key/secret to public repositories

## Helpful Resources

- [Yahoo Fantasy Sports API Documentation](https://developer.yahoo.com/fantasysports/guide/)
- [yahoo-fantasy-api Python wrapper GitHub](https://github.com/spilchen/yahoo_fantasy_api)
- [Yahoo OAuth Guide](https://developer.yahoo.com/oauth2/guide/)

---

**Ready to proceed?** Once you have your credentials set up, we can move on to writing the data collection scripts!
