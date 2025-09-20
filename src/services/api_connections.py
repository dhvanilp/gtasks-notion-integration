"""
API connection handlers for Google Tasks and Notion
"""
import os
import pickle
from notion_client import Client
from googleapiclient.discovery import build

from src.config.settings import *


class APIConnections:
    """Handles API connections for Google Tasks and Notion"""
    
    def __init__(self):
        self.service = None
        self.notion = None
        self._setup_google_tasks()
        self._setup_notion()
    
    def _setup_google_tasks(self):
        """Set up the Google Tasks API connection"""
        try:
            credentials = pickle.load(open(PROJECT_LOCATION + 'token.pkl', 'rb'))
            self.service = build('tasks', 'v1', credentials=credentials)
            
            # Test the connection
            print("Verifying the Google Tasks API token...\n")
            test_list = self.service.tasklists().get(tasklist=DEFAULT_LIST_ID).execute()
            print("Google Tasks API token is valid!\n")
            
        except Exception as e:
            print("Attempting to refresh the Google Tasks API token...\n")
            self._refresh_google_tasks_token()
    
    def _refresh_google_tasks_token(self):
        """Refresh the Google Tasks API token using OAuth flow"""
        try:
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            # OAuth 2.0 scopes for Google Tasks
            SCOPES = ['https://www.googleapis.com/auth/tasks']
            
            creds = None
            # Load existing token if available
            token_file = PROJECT_LOCATION + 'token.pkl'
            if os.path.exists(token_file):
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If there are no valid credentials, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        PROJECT_LOCATION + 'client_secret.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('tasks', 'v1', credentials=creds)
            
            # Test the connection
            test_list = self.service.tasklists().get(tasklist=DEFAULT_LIST_ID).execute()
            print("Successfully refreshed the Google Tasks API token!\n")
            
        except Exception as e:
            print(f"Could not refresh the Google Tasks API token: {e}\n")
            raise Exception("Failed to establish Google Tasks API connection")
    
    def _setup_notion(self):
        """Set up the Notion API connection"""
        self.notion = Client(auth=NOTION_TOKEN)


# Global API connections instance
api = APIConnections()
service = api.service
notion = api.notion