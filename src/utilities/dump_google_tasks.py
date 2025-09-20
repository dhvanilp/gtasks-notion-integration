#!/usr/bin/env python3
"""
Utility script to dump all Google Tasks data to JSON files
Usage: python3 src/utilities/dump_google_tasks.py
"""
import json
import os
from datetime import datetime
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.services.google_tasks_service import google_tasks_service
from src.services.category_manager import category_manager


def create_dump_directory():
    """Create the dump directory structure"""
    project_root = os.path.join(os.path.dirname(__file__), '..', '..')
    dump_dir = os.path.join(project_root, 'dump', 'google_tasks')
    os.makedirs(dump_dir, exist_ok=True)
    return dump_dir


def dump_all_google_tasks():
    """Dump all Google Tasks data to JSON files"""
    print("🚀 Starting Google Tasks dump...")
    
    # Create dump directory
    dump_dir = create_dump_directory()
    print(f"📁 Created dump directory: {dump_dir}")
    
    # Get timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get all task lists
    all_lists = google_tasks_service.get_all_task_lists()
    print(f"📋 Found {len(all_lists)} task lists")
    
    # Get category mappings for reference
    category_mappings = category_manager.get_all_mappings()
    
    # Prepare dump data
    dump_data = {
        'timestamp': datetime.now().isoformat(),
        'total_lists': len(all_lists),
        'category_mappings': category_mappings,
        'lists': [],
        'all_tasks': []
    }
    
    total_tasks = 0
    
    # Process each list
    for task_list in all_lists:
        list_id = task_list['id']
        list_title = task_list['title']
        
        print(f"📂 Processing list: {list_title}")
        
        # Get tasks from this list (excluding deleted tasks by default)
        tasks_data = google_tasks_service.get_tasks_from_list(
            list_id, 
            max_results=1000,  # Get more tasks
            show_deleted=False  # Exclude deleted tasks (set to True if you need them)
        )
        
        tasks = tasks_data.get('items', [])
        total_tasks += len(tasks)
        print(f"   📝 Found {len(tasks)} tasks")
        
        # Find category name for this list
        category_name = None
        for cat_name, mapped_list_id in category_mappings.items():
            if mapped_list_id == list_id:
                category_name = cat_name
                break
        
        list_info = {
            'list_id': list_id,
            'list_title': list_title,
            'category_name': category_name,
            'task_count': len(tasks),
            'tasks': tasks,
            'list_metadata': task_list
        }
        
        dump_data['lists'].append(list_info)
        dump_data['all_tasks'].extend(tasks)
    
    # Save complete dump
    dump_filename = f"google_tasks_complete_{timestamp}.json"
    dump_filepath = os.path.join(dump_dir, dump_filename)
    
    with open(dump_filepath, 'w', encoding='utf-8') as f:
        json.dump(dump_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Complete dump saved: {dump_filename}")
    
    # Save individual list files
    for list_info in dump_data['lists']:
        safe_title = "".join(c for c in list_info['list_title'] if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        list_filename = f"{safe_title}_{timestamp}.json"
        list_filepath = os.path.join(dump_dir, list_filename)
        
        with open(list_filepath, 'w', encoding='utf-8') as f:
            json.dump(list_info, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 List saved: {list_filename}")
    
    # Print summary
    print("\n" + "="*60)
    print("📋 GOOGLE TASKS DUMP SUMMARY")
    print("="*60)
    print(f"Total Lists: {len(all_lists)}")
    print(f"Total Tasks: {total_tasks}")
    print(f"Dump Location: {dump_dir}")
    print(f"Timestamp: {timestamp}")
    
    print(f"\n📂 Lists breakdown:")
    for lst in dump_data['lists']:
        category_info = f" → {lst['category_name']}" if lst['category_name'] else " (unmapped)"
        print(f"   • {lst['list_title']}: {lst['task_count']} tasks{category_info}")
    
    return dump_data, dump_dir


if __name__ == "__main__":
    try:
        dump_data, dump_dir = dump_all_google_tasks()
        print("\n✅ Google Tasks dump completed successfully!")
        print(f"🗂️  Files saved in: {dump_dir}")
        
    except Exception as e:
        print(f"❌ Error during dump: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)