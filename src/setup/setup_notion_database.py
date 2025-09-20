#!/usr/bin/env python3
"""
Setup script to add missing properties to the Notion database
"""
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.api_connections import notion
from config.settings import (
    NOTION_DATABASE_ID, 
    NOTION_GTASKS_LIST_ID
)


def check_database_properties():
    """Check which properties exist in the Notion database"""
    try:
        database = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        
        print("Current Notion Database Properties:")
        existing_props = set()
        for prop_name, prop_data in database['properties'].items():
            prop_type = prop_data.get('type', 'unknown')
            print(f"  ✅ {prop_name}: {prop_type}")
            existing_props.add(prop_name)
        
        # Check for missing required properties
        required_props = {
            NOTION_GTASKS_LIST_ID: 'rich_text'
        }
        
        missing_props = {}
        for prop_name, prop_type in required_props.items():
            if prop_name not in existing_props:
                missing_props[prop_name] = prop_type
                print(f"  ❌ Missing: {prop_name} ({prop_type})")
        
        return missing_props
        
    except Exception as e:
        print(f"Error checking database properties: {e}")
        return None


def add_missing_properties(missing_props):
    """Add missing properties to the Notion database"""
    if not missing_props:
        print("\n✅ All required properties exist!")
        return True
    
    print(f"\n📝 Adding {len(missing_props)} missing properties...")
    
    try:
        # Prepare properties to add
        properties_to_add = {}
        
        for prop_name, prop_type in missing_props.items():
            if prop_type == 'checkbox':
                properties_to_add[prop_name] = {'checkbox': {}}
            elif prop_type == 'rich_text':
                properties_to_add[prop_name] = {'rich_text': {}}
            else:
                print(f"  ⚠️ Unknown property type: {prop_type}")
                continue
            
            print(f"  Adding: {prop_name} ({prop_type})")
        
        # Update database schema
        response = notion.databases.update(
            database_id=NOTION_DATABASE_ID,
            properties=properties_to_add
        )
        
        print("✅ Successfully added missing properties!")
        return True
        
    except Exception as e:
        print(f"❌ Error adding properties: {e}")
        return False


def main():
    print("🔧 Notion Database Setup Tool")
    print("=" * 50)
    
    # Check current properties
    missing_props = check_database_properties()
    
    if missing_props is None:
        print("❌ Failed to check database properties")
        return False
    
    if not missing_props:
        print("\n✅ Database is already properly configured!")
        return True
    
    # Ask user for confirmation
    print(f"\n❓ Add {len(missing_props)} missing properties to the database?")
    response = input("Type 'yes' to proceed: ").lower().strip()
    
    if response != 'yes':
        print("⏹️ Setup cancelled by user")
        return False
    
    # Add missing properties
    success = add_missing_properties(missing_props)
    
    if success:
        print("\n🎉 Database setup complete!")
        print("You can now run the sync operations.")
    else:
        print("\n❌ Database setup failed!")
        print("Please check the error messages above.")
    
    return success


if __name__ == "__main__":
    main()