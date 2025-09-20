#!/usr/bin/env python3
"""
Script to add required integration properties to your Notion database
Run this once to set up the database for syncing
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.config.settings import NOTION_TOKEN, NOTION_DATABASE_ID
import requests

def add_database_properties():
    """Add required properties to the Notion database"""
    
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Properties to add
    properties_to_add = {
        "GTasks Task ID": {"rich_text": {}},
        "GTasks List ID": {"rich_text": {}},
        "Last Synced": {"date": {}}
    }
    
    print("Adding integration properties to Notion database...")
    print(f"Database ID: {NOTION_DATABASE_ID}")
    print()
    
    # Get current database properties first
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Error getting database: {response.status_code}")
        print(response.text)
        return False
    
    current_properties = response.json().get("properties", {})
    
    # Check which properties already exist
    existing_props = []
    missing_props = {}
    
    for prop_name, prop_config in properties_to_add.items():
        if prop_name in current_properties:
            existing_props.append(prop_name)
        else:
            missing_props[prop_name] = prop_config
    
    if existing_props:
        print("✅ Already exist:")
        for prop in existing_props:
            print(f"   - {prop}")
        print()
    
    if not missing_props:
        print("🎉 All required properties already exist!")
        return True
    
    print("➕ Adding missing properties:")
    for prop in missing_props.keys():
        print(f"   - {prop}")
    print()
    
    # Update database with missing properties
    update_data = {
        "properties": {**current_properties, **missing_props}
    }
    
    response = requests.patch(url, headers=headers, json=update_data)
    
    if response.status_code == 200:
        print("🎉 Successfully added all missing properties!")
        return True
    else:
        print(f"❌ Error updating database: {response.status_code}")
        print(response.text)
        return False

if __name__ == "__main__":
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN not configured in settings.py")
        sys.exit(1)
    
    if not NOTION_DATABASE_ID:
        print("❌ NOTION_DATABASE_ID not configured in settings.py")
        sys.exit(1)
    
    success = add_database_properties()
    
    if success:
        print("\n✅ Database is ready for syncing!")
        print("You can now run: python3 main.py")
    else:
        print("\n❌ Failed to update database properties")
        sys.exit(1)