#!/usr/bin/env python3
"""
Helper script to get your Google Tasks list IDs
Run this after setting up OAuth credentials
"""

import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_gtasks_lists():
    """Get all Google Tasks lists with their IDs"""
    creds = None
    
    # Check if token.pkl exists
    if os.path.exists('token.pkl'):
        with open('token.pkl', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pkl', 'wb') as token:
            pickle.dump(creds, token)

    service = build('tasks', 'v1', credentials=creds)
    
    # Get all task lists
    results = service.tasklists().list().execute()
    items = results.get('items', [])

    if not items:
        print('No task lists found.')
        return

    print("\n🗂️  Your Google Tasks Lists:")
    print("=" * 50)
    for item in items:
        print(f"📝 List Name: {item['title']}")
        print(f"🔑 List ID: {item['id']}")
        print("-" * 30)

    print("\n💡 Copy these IDs to your configuration!")

if __name__ == '__main__':
    try:
        get_gtasks_lists()
    except FileNotFoundError:
        print("❌ client_secret.json not found!")
        print("Please download your OAuth credentials from Google Cloud Console")
        print("and save as 'client_secret.json' in this directory.")
    except Exception as e:
        print(f"❌ Error: {e}")