"""
Sync operations from Google Tasks to Notion
"""
from datetime import datetime, timedelta

from src.config.settings import *
# Services imported lazily to avoid API connection issues during import
from src.utils.date_helpers import (
    add_timezone_for_notion, 
    datetime_to_string, 
    parse_datetime_string,
    convert_timezone
)
from src.utils.notion_helpers import make_one_line_plain_text
from src.services.category_manager import category_manager


def import_new_gtasks():
    """Import new Google Tasks to Notion"""
    from src.services.notion_service import notion_service
    from src.services.google_tasks_service import google_tasks_service
    
    print("Adding new Google Tasks to Notion...\n")

    # Get all Notion tasks that have GTasks IDs (to check for orphaned Google Tasks)
    query_filter = {
        'property': NOTION_GTASKS_TASK_ID, 
        'rich_text': {'is_not_empty': True}
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
    gtasks_ids_in_notion = [
        make_one_line_plain_text(page['properties'][NOTION_GTASKS_TASK_ID]['rich_text']) 
        for page in all_notion_results
    ]
    
    print(f'Found {len(all_notion_results)} existing Notion tasks with GTasks IDs')

    # Get all Google Tasks from mapped category lists
    all_gtasks = []
    gtasks_list_ids = []
    
    # Ensure mappings are up to date
    category_mappings = category_manager.refresh_mappings()
    
    for category_name, list_id in category_mappings.items():
        
        # Build date filters
        if PAST_WEEKS_TO_SYNC >= 0 or FUTURE_WEEKS_TO_SYNC >= 0:
            max_date = add_timezone_for_notion(
                datetime_to_string(datetime.now() + timedelta(weeks=FUTURE_WEEKS_TO_SYNC))
            )
            min_date = add_timezone_for_notion(
                datetime_to_string(datetime.now() - timedelta(weeks=PAST_WEEKS_TO_SYNC))
            )
            
            if PAST_WEEKS_TO_SYNC >= 0 and FUTURE_WEEKS_TO_SYNC >= 0:
                gtasks_results = google_tasks_service.get_tasks_from_list(
                    list_id, due_min=min_date, due_max=max_date
                )
            elif PAST_WEEKS_TO_SYNC >= 0:
                gtasks_results = google_tasks_service.get_tasks_from_list(
                    list_id, due_min=min_date
                )
            elif FUTURE_WEEKS_TO_SYNC >= 0:
                gtasks_results = google_tasks_service.get_tasks_from_list(
                    list_id, due_max=max_date
                )
        else:
            gtasks_results = google_tasks_service.get_tasks_from_list(list_id)

        # Also get tasks without dates
        all_tasks_results = google_tasks_service.get_tasks_from_list(list_id)
        gtasks_without_dates = [
            task for task in all_tasks_results['items'] 
            if 'due' not in task
        ]
        
        if 'items' in gtasks_results:
            gtasks_results['items'].extend(gtasks_without_dates)
        
            for task in gtasks_results['items']:
                all_gtasks.append(task)
                gtasks_list_ids.append(list_id)

    if not all_gtasks:
        print("No new Google Tasks to add to Notion\n")
        return

    # Extract task data
    gtasks_data = []
    
    for i, task in enumerate(all_gtasks):
        task_data = _extract_gtasks_data(task, gtasks_list_ids[i])
        gtasks_data.append(task_data)

    # Find tasks that are in Google Tasks but not in Notion
    orphaned_task_indices = []
    truly_new_task_indices = []
    
    for i, task in enumerate(all_gtasks):
        task_id = task['id']
        if task_id not in gtasks_ids_in_notion:
            # Check if this might be an orphaned task (from deleted Notion page)
            # For now, we'll ask the user to confirm or implement heuristics
            # Simple heuristic: if task was created more than 1 day ago, it might be orphaned
            
            try:
                from src.utils.date_helpers import parse_datetime_string, convert_timezone
                task_created = convert_timezone(
                    parse_datetime_string(task['updated'][:-5], '%Y-%m-%dT%H:%M:%S')
                )
                now = convert_timezone(datetime.now())
                
                # If task is older than 1 day, it might be orphaned
                if (now - task_created).days > 1:
                    print(f"⚠️  Found potentially orphaned Google Task: '{task.get('title', 'No title')}'")
                    print(f"   Created: {task_created}")
                    print(f"   This task exists in Google Tasks but not in Notion.")
                    print(f"   This might happen if you deleted the Notion page directly.")
                    print(f"   Skipping import to avoid recreating deleted tasks.")
                    orphaned_task_indices.append(i)
                else:
                    truly_new_task_indices.append(i)
            except:
                # If we can't parse the date, treat as new
                truly_new_task_indices.append(i)

    if len(truly_new_task_indices) == 0:
        if len(orphaned_task_indices) > 0:
            print(f"Found {len(orphaned_task_indices)} potentially orphaned Google Tasks (skipped import)")
            print("If you want to re-import these tasks, delete them from Google Tasks first.\n")
        else:
            print("No new Google Tasks to add to Notion\n")
        return

    # Create new Notion tasks (only truly new ones)
    for index in truly_new_task_indices:
        task_data = gtasks_data[index]
        print(f'Creating new Notion task: {task_data["name"]} in category: {task_data["notion_list_name"]}')
        notion_service.create_task(
            task_data['name'],
            task_data['date'],
            task_data['description'],
            task_data['notion_list_name'],
            task_data['gtasks_id'],
            task_data['gtasks_list_id'],
            task_data['gtasks_status']
        )
        
    if len(orphaned_task_indices) > 0:
        print(f"\n⚠️  Note: Skipped {len(orphaned_task_indices)} potentially orphaned Google Tasks.")
        print("These tasks exist in Google Tasks but not in Notion (possibly from deleted Notion pages).")

    print("Finished adding new Google Tasks to Notion!\n")


def update_notion_from_gtasks():
    """Update Notion tasks that were changed in Google Tasks using bidirectional sync"""
    from src.sync_operations.bidirectional_sync import BidirectionalSyncManager
    
    print("Updating Notion tasks that were changed in Google Tasks...\n")
    
    sync_manager = BidirectionalSyncManager()
    sync_actions = sync_manager.analyze_bidirectional_sync()
    
    # Filter for only GTasks → Notion updates
    gtasks_to_notion_actions = {
        'update_notion_from_gtasks': sync_actions['update_notion_from_gtasks'],
        'update_gtasks_from_notion': [],  # Don't do reverse updates here
        'create_notion_from_gtasks': [],  # Handle creation separately
        'no_sync_needed': [],
        'conflicts': []
    }
    
    if not sync_actions['update_notion_from_gtasks']:
        print("No Notion tasks need updates from Google Tasks\n")
        return
    
    print(f"Found {len(sync_actions['update_notion_from_gtasks'])} tasks to update in Notion")
    changes = sync_manager.execute_bidirectional_sync(gtasks_to_notion_actions, dry_run=False)
    
    print("Finished updating Notion tasks that were changed in Google Tasks!\n")
    return changes


def _extract_gtasks_data(task, gtasks_list_id):
    """Extract data from a Google Task"""
    # Get task name
    try:
        name = task['title']
    except:
        name = 'No Title'

    # Get date
    try:
        date = parse_datetime_string(task['due'], '%Y-%m-%dT%H:%M:%S.000Z')
    except:
        date = ''

    # Get description
    try:
        description = task['notes']
    except:
        description = ''

    # Get status
    status = task['status']

    # Get category name from list mapping with dynamic creation
    all_mappings = category_manager.get_all_mappings()
    notion_list_name = DEFAULT_LIST_NAME  # fallback
    
    # First, try to find existing mapping
    for category, list_id in all_mappings.items():
        if list_id == gtasks_list_id:
            notion_list_name = category
            break
    
    # If no mapping found and we're using default, try to create dynamic mapping
    if notion_list_name == DEFAULT_LIST_NAME and gtasks_list_id != DEFAULT_LIST_ID:
        # Get the GTasks list name to create Notion category
        from src.services.google_tasks_service import google_tasks_service
        gtasks_lists = google_tasks_service.get_all_task_lists()
        
        for gtasks_list in gtasks_lists:
            if gtasks_list['id'] == gtasks_list_id:
                list_title = gtasks_list['title']
                print(f'🔄 Creating dynamic Notion category for GTasks list "{list_title}"')
                
                # Use dynamic category creation
                if category_manager.ensure_gtasks_list_has_notion_category(list_title, gtasks_list_id, create_if_missing=True):
                    notion_list_name = list_title
                    print(f'✅ Dynamic category creation successful: "{list_title}"')
                else:
                    print(f'⚠️ Dynamic category creation failed for "{list_title}", using default')
                break

    return {
        'name': name,
        'date': date,
        'description': description,
        'gtasks_status': status,
        'gtasks_id': task['id'],
        'gtasks_list_id': gtasks_list_id,
        'notion_list_name': notion_list_name
    }