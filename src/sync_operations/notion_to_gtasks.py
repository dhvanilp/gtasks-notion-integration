"""
Sync operations from Notion to Google Tasks
"""
from datetime import datetime, timedelta

from src.config.settings import *
# Services imported lazily to avoid API connection issues during import
from src.utils.date_helpers import (
    add_timezone_for_notion, 
    datetime_to_string, 
    parse_datetime_string, 
    parse_date_string
)
from src.utils.notion_helpers import make_one_line_plain_text, make_description
from src.services.category_manager import category_manager
from src.services.batch_operations import batch_operations_service
from src.utils.sync_reporter import sync_reporter


def import_new_notion_tasks():
    """Import new Notion tasks to Google Tasks using batch operations"""
    from src.services.notion_service import notion_service
    from src.services.google_tasks_service import google_tasks_service
    
    sync_reporter.log_substep("Scanning for orphaned Notion tasks", "Looking for tasks without GTasks IDs", "processing")

    # Build query for tasks without GTasks ID (new tasks)
    query_filter = {
        'property': NOTION_GTASKS_TASK_ID,
        'rich_text': {'is_empty': True}
    }

    # For orphaned task sync, we should sync ALL tasks without GTasks IDs
    # regardless of date filters to ensure nothing gets left behind
    # The date filters are more relevant for ongoing sync operations
    
    # Skip date filters for initial orphaned task sync
    # This ensures all existing Notion tasks get proper GTasks IDs
    if False and (PAST_WEEKS_TO_SYNC >= 0 or FUTURE_WEEKS_TO_SYNC >= 0):
        max_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() + timedelta(weeks=FUTURE_WEEKS_TO_SYNC))
        )
        min_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() - timedelta(weeks=PAST_WEEKS_TO_SYNC))
        )
        
        # Convert single property filter to 'and' structure for date filters
        base_filter = query_filter.copy()
        query_filter = {'and': [base_filter]}
        
        if PAST_WEEKS_TO_SYNC >= 0 and FUTURE_WEEKS_TO_SYNC >= 0:
            query_filter['and'].extend([
                {'or': [
                    {'property': NOTION_DATE, 'date': {'on_or_after': min_date}}, 
                    {'property': NOTION_DATE, 'date': {'is_empty': True}}
                ]},
                {'or': [
                    {'property': NOTION_DATE, 'date': {'on_or_before': max_date}}, 
                    {'property': NOTION_DATE, 'date': {'is_empty': True}}
                ]}
            ])
        elif PAST_WEEKS_TO_SYNC >= 0:
            query_filter['and'].append({
                'or': [
                    {'property': NOTION_DATE, 'date': {'on_or_after': min_date}}, 
                    {'property': NOTION_DATE, 'date': {'is_empty': True}}
                ]
            })
        elif FUTURE_WEEKS_TO_SYNC >= 0:
            query_filter['and'].append({
                'or': [
                    {'property': NOTION_DATE, 'date': {'on_or_before': max_date}}, 
                    {'property': NOTION_DATE, 'date': {'is_empty': True}}
                ]
            })

    # Get all unsynced Notion tasks
    notion_pages = notion_service.query_database(query_filter)
    
    # Handle pagination
    all_results = notion_pages['results']
    while notion_pages['has_more']:
        notion_pages = notion_service.query_database(query_filter, notion_pages['next_cursor'])
        all_results.extend(notion_pages['results'])
        if not notion_pages['next_cursor']:
            break

    if len(all_results) == 0:
        sync_reporter.log_substep("No orphaned tasks found", "All Notion tasks have GTasks IDs", "success")
        return

    sync_reporter.log_substep(f"Found {len(all_results)} orphaned tasks", "Preparing batch creation", "warning")
    
    # Prepare batch create data
    batch_creates = []
    notion_page_data = []
    
    for page in all_results:
        task_data = _extract_notion_task_data(page)
        
        sync_reporter.log_substep(f"Processing: {task_data['name'][:40]}", 
                                f"Category: {task_data['notion_list_name']}", "info")
        
        # Store for later Notion updates
        notion_page_data.append({
            'page_id': page['id'],
            'task_data': task_data,
            'task_name': task_data['name']
        })
        
        # Prepare for batch GTasks creation
        batch_creates.append({
            'task_data': task_data,
            'gtasks_list_id': task_data['gtasks_list_id']
        })
    
    # Execute batch Google Tasks creation
    sync_reporter.log_batch_operation("GTasks Creation", len(batch_creates))
    start_time = datetime.now()
    gtasks_results = batch_operations_service.batch_create_gtasks(batch_creates)
    duration = (datetime.now() - start_time).total_seconds()
    
    # Process results and update Notion with GTasks IDs
    successful_creates = 0
    failed_creates = 0
    
    for i, result in enumerate(gtasks_results):
        notion_data = notion_page_data[i]
        
        if 'error' not in result:
            # Success - update Notion with GTasks ID
            gtasks_id = result['id']
            task_data = notion_data['task_data']
            
            _update_notion_after_gtasks_creation(
                notion_data['page_id'], 
                gtasks_id, 
                task_data
            )
            
            successful_creates += 1
            sync_reporter.record_notion_to_gtasks('created', notion_data['task_name'], {
                'gtasks_id': gtasks_id,
                'category': task_data['notion_list_name'],
                'icon_updated': True
            })
            
        else:
            failed_creates += 1
            sync_reporter.record_error('gtasks_creation_failed', 
                                     f"Failed to create GTasks for: {notion_data['task_name']}", 
                                     {'error': result.get('error', 'Unknown error')})
    
    # Summary
    if successful_creates > 0:
        sync_reporter.log_substep(f"Successfully created {successful_creates} Google Tasks", 
                                f"Completed in {duration:.1f}s", "success")
    if failed_creates > 0:
        sync_reporter.log_substep(f"Failed to create {failed_creates} Google Tasks", 
                                "Check error details above", "error")


def update_gtasks_from_notion():
    """Update Google Tasks that were changed in Notion using bidirectional sync"""
    from src.sync_operations.bidirectional_sync import BidirectionalSyncManager
    
    print("Updating Google Tasks that were changed in Notion...\n")
    
    sync_manager = BidirectionalSyncManager()
    sync_actions = sync_manager.analyze_bidirectional_sync()
    
    # Filter for only Notion → GTasks updates
    notion_to_gtasks_actions = {
        'update_notion_from_gtasks': [],  # Don't do reverse updates here
        'update_gtasks_from_notion': sync_actions['update_gtasks_from_notion'],
        'create_notion_from_gtasks': [],
        'no_sync_needed': [],
        'conflicts': []
    }
    
    if not sync_actions['update_gtasks_from_notion']:
        print("No Google Tasks need updates from Notion\n")
        return
    
    print(f"Found {len(sync_actions['update_gtasks_from_notion'])} tasks to update in Google Tasks")
    changes = sync_manager.execute_bidirectional_sync(notion_to_gtasks_actions, dry_run=False)
    
    print("Finished updating Google Tasks that were changed in Notion!\n")
    return changes


def _extract_notion_task_data(page):
    """Extract task data from a Notion page"""
    # Get task name
    try:
        task_name = page['properties'][NOTION_TASK_NAME]['title'][0]['plain_text']
    except:
        task_name = 'No Title'

    # Get status and convert to Google Tasks status
    try:
        checkbox_status = page['properties'][NOTION_STATUS]['checkbox']
        if checkbox_status:
            gtasks_status = GOOGLE_DONE_STATUS
        else:
            gtasks_status = GOOGLE_TO_DO_STATUS
    except:
        gtasks_status = GOOGLE_TO_DO_STATUS

    # Get date from the Date field (not Due Date)
    try:
        task_date = parse_datetime_string(
            page['properties'][NOTION_DATE]['date']['start'][:-6], 
            '%Y-%m-%dT%H:%M:%S.000'
        )
    except:
        try:
            task_date = parse_date_string(
                page['properties'][NOTION_DATE]['date']['start'], 
                '%Y-%m-%d'
            )
        except:
            task_date = ''

    # Get description
    try:
        description = make_description(page['properties'][NOTION_DESCRIPTION]['rich_text'])
    except:
        description = ''

    # Get list info using category manager with dynamic creation
    try:
        notion_list_name = page['properties'][NOTION_LIST_NAME]['select']['name']
        # Use dynamic category creation - will create GTasks list if it doesn't exist
        gtasks_list_id = category_manager.ensure_category_exists(notion_list_name, create_if_missing=True)
        
        # If creation failed, use default
        if not gtasks_list_id:
            gtasks_list_id = DEFAULT_LIST_ID
            print(f'⚠️ Failed to create/find GTasks list for category "{notion_list_name}", using default')
    except:
        gtasks_list_id = DEFAULT_LIST_ID
        notion_list_name = ''

    return {
        'name': task_name,
        'gtasks_status': gtasks_status,
        'date': task_date,
        'description': description,
        'gtasks_list_id': gtasks_list_id,
        'notion_list_name': notion_list_name
    }


def _update_notion_after_gtasks_creation(page_id, gtasks_id, task_data):
    """Update Notion task after Google Task creation with icon and set Due Date"""
    from src.services.api_connections import notion
    from src.services.notion_service import notion_service
    
    # Determine completion status and appropriate icon
    notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
    task_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
    
    # Prepare properties to update
    properties = {
        NOTION_GTASKS_TASK_ID: {
            'rich_text': [{'text': {'content': gtasks_id}}]
        },
        NOTION_GTASKS_LIST_ID: {
            'rich_text': [{'text': {'content': task_data['gtasks_list_id']}}]
        },
        NOTION_LAST_SYNCED: {
            'date': {
                'start': add_timezone_for_notion(
                    datetime_to_string(datetime.now())
                ),
                'end': None
            }
        }
    }
    
    # If task has a date, set Due Date to Date + 1 week
    if task_data['date']:
        try:
            from src.utils.date_helpers import add_week_to_date_string
            due_date_str = add_week_to_date_string(task_data['date'])
            properties[NOTION_DUE_DATE] = {
                'date': {
                    'start': due_date_str,
                    'end': None
                }
            }
        except Exception as e:
            print(f"Warning: Could not set due date for task {task_data['title']}: {e}")
    
    notion.pages.update(
        page_id=page_id,
        icon={
            'type': 'emoji',
            'emoji': task_icon
        },
        properties=properties
    )

    # Set default list if empty
    if task_data['notion_list_name'] == '':
        notion.pages.update(
            page_id=page_id,
            properties={
                NOTION_LIST_NAME: {
                    'select': {'name': DEFAULT_LIST_NAME}
                }
            }
        )