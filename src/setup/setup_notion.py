#!/usr/bin/env python3
"""
Convenience script to set up Notion database properties
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    from utilities.add_notion_properties import add_database_properties
    from config.settings import NOTION_TOKEN, NOTION_DATABASE_ID
    
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN not configured in src/config/settings.py")
        sys.exit(1)
    
    if not NOTION_DATABASE_ID:
        print("❌ NOTION_DATABASE_ID not configured in src/config/settings.py")
        sys.exit(1)¥
    
    success = add_database_properties()
    
    if success:
        print("\n✅ Database is ready for syncing!")
        print("You can now run: python3 main.py")
    else:
        print("\n❌ Failed to update database properties")
        sys.exit(1)