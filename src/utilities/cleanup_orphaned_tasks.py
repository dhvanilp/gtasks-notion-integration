#!/usr/bin/env python3
"""
Cleanup script for orphaned Google Tasks

This script helps you manage Google Tasks that no longer have corresponding Notion pages.
This can happen when you delete Notion database pages directly instead of marking them as deleted.
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.category_manager import category_manager
from src.services.notion_service import notion_service
from src.services.google_tasks_service import google_tasks_service
from src.utils.notion_helpers import make_one_line_plain_text


def main():
    """Main cleanup function"""
    print("\n" + "="*70)
    print("Google Tasks Orphan Cleanup Tool")
    print("="*70 + "\n")

    try:
        # Initialize API connections
        print("Initializing API connections...")
        from src.services.api_connections import api
        print("API connections established!\n")

        while True:
            print("\nChoose an action:")
            print("1. Scan for orphaned Google Tasks")
            print("2. Clean up orphaned Google Tasks (delete them)")
            print("3. Re-import orphaned Google Tasks to Notion")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                scan_orphaned_tasks()
            elif choice == '2':
                cleanup_orphaned_tasks()
            elif choice == '3':
                reimport_orphaned_tasks()
            elif choice == '4':
                print("\nGoodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def find_orphaned_tasks():
    """Find Google Tasks that don't have corresponding Notion pages"""
    print("Scanning for orphaned Google Tasks...")
    
    # Get all synced Notion tasks
    query_filter = {
        "and": [
            {
                'property': 'Synced', 
                'checkbox': {'equals': True}
            }
        ]
    }

    notion_pages = notion_service.query_database(query_filter)
    
    # Handle pagination
    all_notion_results = notion_pages['results']
    while notion_pages['has_more']:
        notion_pages = notion_service.query_database(query_filter, notion_pages['next_cursor'])
        all_notion_results.extend(notion_pages['results'])
        if not notion_pages['next_cursor']:
            break

    # Get existing Google Tasks IDs in Notion
    gtasks_ids_in_notion = set()
    for page in all_notion_results:
        gtask_id = make_one_line_plain_text(page['properties']['GTasks Task ID']['rich_text'])
        if gtask_id:
            gtasks_ids_in_notion.add(gtask_id)

    # Get all Google Tasks from mapped lists
    all_gtasks = []
    all_mappings = category_manager.get_all_mappings()
    
    for category_name, list_id in all_mappings.items():
        gtasks_results = google_tasks_service.get_tasks_from_list(list_id)
        if 'items' in gtasks_results:
            for task in gtasks_results['items']:
                all_gtasks.append((task, category_name))

    # Find orphaned tasks
    orphaned_tasks = []
    for task, category in all_gtasks:
        task_id = task['id']
        if task_id not in gtasks_ids_in_notion:
            # Check if it's actually orphaned (older than 1 hour)
            try:
                from src.utils.date_helpers import parse_datetime_string, convert_timezone
                task_updated = convert_timezone(
                    parse_datetime_string(task['updated'][:-5], '%Y-%m-%dT%H:%M:%S')
                )
                now = convert_timezone(datetime.now())
                
                # If task is older than 1 hour, consider it potentially orphaned
                if (now - task_updated).total_seconds() > 3600:
                    orphaned_tasks.append((task, category))
            except:
                # If we can't parse the date, include it
                orphaned_tasks.append((task, category))

    return orphaned_tasks


def scan_orphaned_tasks():
    """Scan and display orphaned tasks"""
    print("\n" + "-" * 50)
    print("Scanning for Orphaned Google Tasks")
    print("-" * 50)
    
    orphaned_tasks = find_orphaned_tasks()
    
    if not orphaned_tasks:
        print("✅ No orphaned Google Tasks found!")
        return
    
    print(f"Found {len(orphaned_tasks)} potentially orphaned Google Tasks:\n")
    
    for i, (task, category) in enumerate(orphaned_tasks, 1):
        title = task.get('title', 'No title')
        updated = task.get('updated', 'Unknown')
        task_id = task['id']
        
        print(f"{i}. {title}")
        print(f"   Category: {category}")
        print(f"   Last updated: {updated}")
        print(f"   Task ID: {task_id}")
        print()


def cleanup_orphaned_tasks():
    """Delete orphaned Google Tasks"""
    print("\n" + "-" * 50)
    print("Cleanup Orphaned Google Tasks")
    print("-" * 50)
    
    orphaned_tasks = find_orphaned_tasks()
    
    if not orphaned_tasks:
        print("✅ No orphaned Google Tasks found!")
        return
    
    print(f"Found {len(orphaned_tasks)} potentially orphaned Google Tasks")
    print("These tasks exist in Google Tasks but not in Notion.")
    print("This usually happens when you delete Notion pages directly.\n")
    
    for i, (task, category) in enumerate(orphaned_tasks[:5], 1):  # Show first 5
        title = task.get('title', 'No title')
        print(f"{i}. {title} (Category: {category})")
    
    if len(orphaned_tasks) > 5:
        print(f"... and {len(orphaned_tasks) - 5} more")
    
    print(f"\n⚠️  WARNING: This will permanently delete {len(orphaned_tasks)} Google Tasks!")
    confirm = input("Are you sure you want to delete these tasks? (type 'DELETE' to confirm): ").strip()
    
    if confirm != 'DELETE':
        print("Cancelled.")
        return
    
    print("\nDeleting orphaned Google Tasks...")
    deleted_count = 0
    
    for task, category in orphaned_tasks:
        list_id = category_manager.get_list_id_for_category(category)
        if list_id:
            success = google_tasks_service.delete_task(list_id, task['id'])
            if success:
                deleted_count += 1
                print(f"✅ Deleted: {task.get('title', 'No title')}")
            else:
                print(f"❌ Failed to delete: {task.get('title', 'No title')}")
    
    print(f"\n✅ Deleted {deleted_count} orphaned Google Tasks")


def reimport_orphaned_tasks():
    """Re-import orphaned Google Tasks to Notion"""
    print("\n" + "-" * 50)
    print("Re-import Orphaned Google Tasks")
    print("-" * 50)
    
    orphaned_tasks = find_orphaned_tasks()
    
    if not orphaned_tasks:
        print("✅ No orphaned Google Tasks found!")
        return
    
    print(f"Found {len(orphaned_tasks)} potentially orphaned Google Tasks")
    print("This will create new Notion pages for these tasks.\n")
    
    for i, (task, category) in enumerate(orphaned_tasks[:5], 1):  # Show first 5
        title = task.get('title', 'No title')
        print(f"{i}. {title} (Category: {category})")
    
    if len(orphaned_tasks) > 5:
        print(f"... and {len(orphaned_tasks) - 5} more")
    
    confirm = input(f"\nRe-import {len(orphaned_tasks)} tasks to Notion? (y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    print("\nRe-importing orphaned Google Tasks to Notion...")
    imported_count = 0
    
    from src.sync_operations.gtasks_to_notion import _extract_gtasks_data
    
    for task, category in orphaned_tasks:
        try:
            list_id = category_manager.get_list_id_for_category(category)
            task_data = _extract_gtasks_data(task, list_id)
            
            notion_service.create_task(
                task_data['name'],
                task_data['date'],
                task_data['description'],
                task_data['notion_list_name'],
                task_data['gtasks_id'],
                task_data['gtasks_list_id'],
                task_data['gtasks_status']
            )
            
            imported_count += 1
            print(f"✅ Imported: {task.get('title', 'No title')}")
        except Exception as e:
            print(f"❌ Failed to import: {task.get('title', 'No title')} - {e}")
    
    print(f"\n✅ Re-imported {imported_count} orphaned Google Tasks to Notion")


if __name__ == "__main__":
    main()