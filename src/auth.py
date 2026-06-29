"""
Yahoo Fantasy Sports OAuth Authentication Module

Handles OAuth2 authentication with Yahoo Fantasy Sports API.
"""

import json
import os
from pathlib import Path
from yahoo_oauth import OAuth2
import logging

logger = logging.getLogger(__name__)



class YahooAuthenticator:
    """Handle Yahoo Fantasy Sports API authentication."""
    
    def __init__(self, credentials_file='config/credentials.json', 
                 oauth_file='config/oauth2.json'):
        """
        Initialize authenticator.
        
        Args:
            credentials_file: Path to JSON file with consumer_key and consumer_secret
            oauth_file: Path to store OAuth tokens
        """
        self.credentials_file = Path(credentials_file)
        self.oauth_file = Path(oauth_file)
        self.oauth = None
        
    def authenticate(self):
        """
        Authenticate with Yahoo API.
        
        Returns:
            OAuth2 object for making API calls
            
        Raises:
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If credentials are invalid
        """
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n"
                "Please create config/credentials.json with your Yahoo API credentials.\n"
                "See yahoo_api_setup_guide.md for instructions."
            )
        
        # Load credentials
        with open(self.credentials_file, 'r') as f:
            creds = json.load(f)
        
        if 'consumer_key' not in creds or 'consumer_secret' not in creds:
            raise ValueError(
                "credentials.json must contain 'consumer_key' and 'consumer_secret'"
            )
        
        try:
            # Check if we have existing OAuth tokens
            if self.oauth_file.exists():
                logger.info("Using existing OAuth tokens")
                self.oauth = OAuth2(None, None, from_file=str(self.oauth_file))
            else:
                logger.info("Starting OAuth flow - browser will open for authorization")
                # yahoo_oauth reads consumer creds from from_file, so seed it first
                self.oauth_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.oauth_file, 'w') as f:
                    json.dump({
                        'consumer_key': creds['consumer_key'],
                        'consumer_secret': creds['consumer_secret'],
                    }, f)
                self.oauth = OAuth2(None, None, from_file=str(self.oauth_file))
                logger.info(f"OAuth tokens saved to {self.oauth_file}")
            
            # Test the connection
            if not self.oauth.token_is_valid():
                logger.info("Token expired, refreshing...")
                self.oauth.refresh_access_token()
            
            logger.info("Authentication successful!")
            return self.oauth
            
        except Exception as e:
            # Remove seed file if it was created without a valid token
            if self.oauth_file.exists():
                try:
                    with open(self.oauth_file) as f:
                        data = json.load(f)
                    if 'access_token' not in data:
                        self.oauth_file.unlink()
                        logger.debug("Removed incomplete OAuth seed file after failed auth")
                except Exception:
                    pass
            logger.error(f"Authentication failed: {e}")
            raise
    
    def is_authenticated(self):
        """Check if we have valid authentication."""
        if self.oauth is None:
            return False
        return self.oauth.token_is_valid()
    
    def refresh_token(self):
        """Refresh the access token."""
        if self.oauth:
            self.oauth.refresh_access_token()
            logger.info("Access token refreshed")


def main():
    """Test authentication when run directly."""
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        auth = YahooAuthenticator()
        oauth = auth.authenticate()
        print("\n✓ Authentication successful!")
        print(f"✓ Tokens saved to {auth.oauth_file}")
        print("\nYou can now run the data collection script.")
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
