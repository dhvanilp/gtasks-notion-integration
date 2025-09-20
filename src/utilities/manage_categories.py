#!/usr/bin/env python3
"""
Category Management Script for Google Tasks + Notion Integration

This script helps you manage the category mappings between Notion and Google Tasks:
- View current category mappings
- Sync categories from Notion to create Google Tasks lists
- Refresh mappings when new categories are added
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.category_manager import category_manager
from src.services.notion_service import notion_service
from src.services.google_tasks_service import google_tasks_service


def main():
    """Main category management function"""
    print("\n" + "="*70)
    print("Google Tasks + Notion Category Manager")
    print("="*70 + "\n")

    try:
        # Initialize API connections
        print("Initializing API connections...")
        from src.services.api_connections import api
        print("API connections established!\n")

        while True:
            print("\nChoose an action:")
            print("1. View current category mappings")
            print("2. View categories from Notion database")
            print("3. View active categories from Notion tasks")
            print("4. Bidirectional sync (Notion ↔ Google Tasks)")
            print("5. One-way sync (Notion → Google Tasks)")
            print("6. View all Google Tasks lists")
            print("7. Exit")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                view_current_mappings()
            elif choice == '2':
                view_notion_database_categories()
            elif choice == '3':
                view_active_notion_categories()
            elif choice == '4':
                sync_categories()
            elif choice == '5':
                sync_categories_one_way()
            elif choice == '6':
                view_gtasks_lists()
            elif choice == '7':
                print("\nGoodbye!")
                break
            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def view_current_mappings():
    """View current category to Google Tasks list mappings"""
    print("\n" + "-" * 50)
    print("Current Category Mappings")
    print("-" * 50)
    
    mappings = category_manager.get_all_mappings()
    
    if not mappings:
        print("No category mappings found.")
        print("Run option 4 to sync categories and create Google Tasks lists.")
    else:
        print(f"{'Category':<25} {'Google Tasks List ID'}")
        print("-" * 50)
        for category, list_id in mappings.items():
            print(f"{category:<25} {list_id}")


def view_notion_database_categories():
    """View categories from Notion database schema"""
    print("\n" + "-" * 50)
    print("Categories from Notion Database Schema")
    print("-" * 50)
    
    categories = notion_service.get_all_categories()
    
    if not categories:
        print("No categories found in Notion database schema.")
    else:
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")


def view_active_notion_categories():
    """View categories from active Notion tasks"""
    print("\n" + "-" * 50)
    print("Categories from Active Notion Tasks")
    print("-" * 50)
    
    categories = notion_service.get_active_categories_from_tasks()
    
    if not categories:
        print("No categories found in active Notion tasks.")
    else:
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category}")


def sync_categories():
    """Sync categories and create Google Tasks lists (bidirectionally)"""
    print("\n" + "-" * 50)
    print("Bidirectional Category/List Sync")
    print("-" * 50)
    
    print("This will:")
    print("1. Get all categories from your Notion database")
    print("2. Create Google Tasks lists for new categories")
    print("3. Find unmapped Google Tasks lists")
    print("4. Create Notion categories for unmapped lists")
    print("5. Update the mapping file")
    
    confirm = input("\nProceed with bidirectional sync? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    mappings = category_manager.sync_categories_with_gtasks_lists(bidirectional=True)
    
    print("\n✅ Bidirectional category sync completed!")
    print(f"Total mapped categories/lists: {len(mappings)}")
    
    for category, list_id in mappings.items():
        print(f"  • {category} → {list_id}")


def sync_categories_one_way():
    """Sync only Notion → Google Tasks (original functionality)"""
    print("\n" + "-" * 50)
    print("One-Way Sync: Notion Categories → Google Tasks Lists")
    print("-" * 50)
    
    print("This will:")
    print("1. Get all categories from your Notion database")
    print("2. Create Google Tasks lists for new categories")
    print("3. Update the mapping file")
    print("(Note: Won't create Notion categories from Google Tasks lists)")
    
    confirm = input("\nProceed with one-way sync? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    mappings = category_manager.sync_categories_with_gtasks_lists(bidirectional=False)
    
    print("\n✅ One-way category sync completed!")
    print(f"Mapped {len(mappings)} categories:")
    
    for category, list_id in mappings.items():
        print(f"  • {category} → {list_id}")


def view_gtasks_lists():
    """View all Google Tasks lists"""
    print("\n" + "-" * 50)
    print("All Google Tasks Lists")
    print("-" * 50)
    
    lists = google_tasks_service.get_all_task_lists()
    
    if not lists:
        print("No Google Tasks lists found.")
    else:
        print(f"{'List Name':<30} {'List ID'}")
        print("-" * 50)
        for task_list in lists:
            print(f"{task_list['title']:<30} {task_list['id']}")


if __name__ == "__main__":
    main()