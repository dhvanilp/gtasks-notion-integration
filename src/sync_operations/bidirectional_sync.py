"""
Bidirectional sync operations with timestamp comparison
"""
from datetime import datetime, timedelta
from dateutil import parser

from src.config.settings import *
from src.utils.date_helpers import (
    add_timezone_for_notion, 
    datetime_to_string, 
    parse_datetime_string,
    convert_timezone
)
from src.utils.notion_helpers import make_one_line_plain_text, make_description
from src.services.category_manager import category_manager
from src.services.batch_operations import batch_operations_service


class BidirectionalSyncManager:
    """Manages bidirectional sync operations with timestamp comparison"""
    
    def __init__(self):
        # Import services lazily to avoid connection issues
        from src.services.notion_service import notion_service
        from src.services.google_tasks_service import google_tasks_service
        
        self.notion_service = notion_service
        self.google_tasks_service = google_tasks_service
        self.category_mappings = category_manager.get_all_mappings()
    
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string to datetime object (timezone-naive for comparison)"""
        if not timestamp_str:
            return None
        
        try:
            if 'GMT' in timestamp_str or '(' in timestamp_str:
                # Custom format: "September 19, 2025 3:32 PM (GMT+5:30)" (from our last_synced field)
                date_part = timestamp_str.split('(')[0].strip()
                dt = parser.parse(date_part)
                return dt.replace(tzinfo=None)
            else:
                # ISO format: "2025-09-19T10:02:12.870Z" (Google Tasks updated, Notion last_edited_time)
                dt = parser.parse(timestamp_str)
                return dt.replace(tzinfo=None)
        except Exception as e:
            print(f"Error parsing timestamp '{timestamp_str}': {e}")
            return None
    
    def compare_timestamps(self, gtasks_updated, notion_last_edited):
        """Compare timestamps to determine which system has newer data for this specific task"""
        gtasks_time = self.parse_timestamp(gtasks_updated)
        notion_time = self.parse_timestamp(notion_last_edited)
        
        if not gtasks_time and not notion_time:
            return 'unknown'
        elif not gtasks_time:
            return 'notion_newer'
        elif not notion_time:
            return 'gtasks_newer'
        elif gtasks_time > notion_time:
            return 'gtasks_newer'
        elif notion_time > gtasks_time:
            return 'notion_newer'
        else:
            return 'same'
    
    def get_synced_notion_tasks(self):
        """Get all Notion tasks that have GTasks IDs (synced tasks)"""
        # IMPORTANT: Don't use date filters when checking for existing tasks to prevent duplicates!
        # This ensures we find ALL existing synced tasks, not just those within date range
        query_filter = {
            'property': NOTION_GTASKS_TASK_ID, 
            'rich_text': {'is_not_empty': True}
        }
        
        # NOTE: We deliberately do NOT add date filters here to avoid creating duplicates
        # The date filtering should only be applied when actually syncing content, not when
        # determining which tasks already exist
        
        notion_pages = self.notion_service.query_database(query_filter)
        
        # Handle pagination
        all_results = notion_pages['results']
        while notion_pages['has_more']:
            notion_pages = self.notion_service.query_database(query_filter, notion_pages['next_cursor'])
            all_results.extend(notion_pages['results'])
            if not notion_pages['next_cursor']:
                break
        
        return all_results
    
    def get_gtasks_by_list(self):
        """Get all Google Tasks organized by list"""
        all_gtasks_by_list = {}
        
        # Refresh category mappings
        self.category_mappings = category_manager.refresh_mappings()
        
        for category_name, list_id in self.category_mappings.items():
            # Get tasks with date filters if configured
            if PAST_WEEKS_TO_SYNC >= 0 or FUTURE_WEEKS_TO_SYNC >= 0:
                gtasks_results = self._get_filtered_gtasks(list_id)
            else:
                gtasks_results = self.google_tasks_service.get_tasks_from_list(list_id)
            
            # Also get tasks without dates
            all_tasks_results = self.google_tasks_service.get_tasks_from_list(list_id)
            gtasks_without_dates = [
                task for task in all_tasks_results.get('items', [])
                if 'due' not in task
            ]
            
            # Combine tasks with and without dates
            if 'items' in gtasks_results:
                gtasks_results['items'].extend(gtasks_without_dates)
            
            all_gtasks_by_list[list_id] = {
                'category_name': category_name,
                'tasks': gtasks_results.get('items', [])
            }
        
        return all_gtasks_by_list
    
    def analyze_bidirectional_sync(self):
        """Analyze all tasks and determine sync actions needed"""
        print("Analyzing bidirectional sync requirements...\n")
        
        # Get data from both systems
        notion_tasks = self.get_synced_notion_tasks()
        gtasks_by_list = self.get_gtasks_by_list()
        
        # Create lookup structures
        notion_by_gtasks_id = {}
        for page in notion_tasks:
            gtasks_id = make_one_line_plain_text(
                page['properties'][NOTION_GTASKS_TASK_ID]['rich_text']
            )
            if gtasks_id:
                notion_by_gtasks_id[gtasks_id] = page
        
        gtasks_by_id = {}
        for list_id, list_data in gtasks_by_list.items():
            for task in list_data['tasks']:
                gtasks_by_id[task['id']] = {
                    'task': task,
                    'list_id': list_id,
                        'category_name': list_data['category_name']
                    }
        
        # Analyze sync requirements
        sync_actions = {
            'update_notion_from_gtasks': [],
            'update_gtasks_from_notion': [],
            'create_notion_from_gtasks': [],
            'no_sync_needed': [],
            'conflicts': []
        }
        
        # Check tasks that exist in both systems
        for gtasks_id, gtasks_info in gtasks_by_id.items():
            if gtasks_id in notion_by_gtasks_id:
                notion_page = notion_by_gtasks_id[gtasks_id]
                gtasks_task = gtasks_info['task']
                
                # Get timestamps for this specific task
                gtasks_updated = gtasks_task.get('updated')
                notion_last_edited = notion_page.get('last_edited_time')
                
                # Perform per-task timestamp comparison
                comparison = self.compare_timestamps(gtasks_updated, notion_last_edited)
                
                # Per-task timestamp comparison complete
                
                sync_info = {
                    'gtasks_id': gtasks_id,
                    'gtasks_task': gtasks_task,
                    'notion_page': notion_page,
                    'gtasks_info': gtasks_info,
                    'comparison': comparison
                }
                
                # Check for list/category mismatch and other changes
                current_notion_category = notion_page['properties'][NOTION_LIST_NAME]['select']['name'] if notion_page['properties'][NOTION_LIST_NAME]['select'] else ''
                gtasks_category_name = gtasks_info['category_name']
                
                category_mismatch = current_notion_category != gtasks_category_name
                
                # Check for other task content changes
                task_content_differs = self._check_task_content_differs(gtasks_task, notion_page, gtasks_info)
                
                if category_mismatch:
                    print(f"  📁 List/Category change detected for '{gtasks_task.get('title', '')}':")
                    print(f"     Notion: '{current_notion_category}' vs GTasks: '{gtasks_category_name}'")
                    print(f"     GTasks updated: {gtasks_updated}")
                    print(f"     Notion last edited: {notion_last_edited}")
                    print(f"     Timestamp comparison: {comparison}")
                    
                    # For category mismatches, respect timestamp comparison
                    # Moving a task in GTasks updates its timestamp, so GTasks should win if newer
                    if comparison == 'gtasks_newer':
                        print(f"    → GTasks is newer (moved recently), updating Notion category")
                        sync_actions['update_notion_from_gtasks'].append(sync_info)
                    elif comparison == 'notion_newer':
                        print(f"    → Notion is newer (category changed recently), updating GTasks list")
                        sync_actions['update_gtasks_from_notion'].append(sync_info)
                    elif comparison == 'same':
                        # For same timestamps with category mismatch, prefer GTasks as source of truth
                        # since list membership is managed in GTasks
                        print(f"    → Timestamps equal, defaulting to GTasks list (source of truth)")
                        sync_actions['update_notion_from_gtasks'].append(sync_info)
                    else:
                        print(f"    → Conflict detected, needs manual resolution")
                        sync_actions['conflicts'].append(sync_info)
                        
                elif task_content_differs and comparison == 'gtasks_newer':
                    # Check what type of content changed
                    change_types = self._get_change_types(gtasks_task, notion_page, gtasks_info)
                    change_desc = ", ".join(change_types)
                    print(f"  📝 Content changed in GTasks for '{gtasks_task.get('title', '')}' ({change_desc}) - timestamp: {comparison}")
                    sync_actions['update_notion_from_gtasks'].append(sync_info)
                    
                elif task_content_differs and comparison == 'notion_newer':
                    # Check what type of content changed
                    change_types = self._get_change_types(gtasks_task, notion_page, gtasks_info)
                    change_desc = ", ".join(change_types)
                    print(f"  📝 Content changed in Notion for '{gtasks_task.get('title', '')}' ({change_desc}) - timestamp: {comparison}")
                    sync_actions['update_gtasks_from_notion'].append(sync_info)
                    
                elif comparison == 'same' and not task_content_differs:
                    sync_actions['no_sync_needed'].append(sync_info)
                    
                else:
                    # Handle other timestamp-based sync scenarios
                    if comparison == 'unknown':
                        print(f"  ⚠️ Unknown timestamp state for '{gtasks_task.get('title', '')}', skipping")
                        sync_actions['conflicts'].append(sync_info)
                    elif comparison not in ['same', 'gtasks_newer', 'notion_newer']:
                        sync_actions['conflicts'].append(sync_info)
            else:
                # Task exists in GTasks but not in Notion (or not synced)
                sync_actions['create_notion_from_gtasks'].append({
                    'gtasks_id': gtasks_id,
                    'gtasks_task': gtasks_info['task'],
                    'gtasks_info': gtasks_info
                })
        
        return sync_actions
    
    def _check_task_content_differs(self, gtasks_task, notion_page, gtasks_info):
        """Check if task content (other than category) differs between systems"""
        try:
            # Compare task name
            gtasks_title = gtasks_task.get('title', '').strip()
            notion_title = notion_page['properties'][NOTION_TASK_NAME]['title'][0]['plain_text'].strip() if notion_page['properties'][NOTION_TASK_NAME]['title'] else ''
            
            if gtasks_title != notion_title:
                return True
            
            # Compare task status
            gtasks_status = gtasks_task.get('status', '')
            notion_checkbox = notion_page['properties'][NOTION_STATUS]['checkbox']
            
            # Convert statuses for comparison
            gtasks_completed = (gtasks_status == GOOGLE_DONE_STATUS)
            notion_completed = notion_checkbox
            
            if gtasks_completed != notion_completed:
                return True
            
            # Compare descriptions
            gtasks_description = gtasks_task.get('notes', '').strip()
            notion_description = make_description(notion_page['properties'][NOTION_DESCRIPTION]['rich_text']).strip()
            
            if gtasks_description != notion_description:
                return True
            
            # Compare due dates
            gtasks_due = gtasks_task.get('due', '')
            notion_due = ''
            try:
                if notion_page['properties'][NOTION_DATE]['date']:
                    notion_due = notion_page['properties'][NOTION_DATE]['date']['start']
            except:
                pass
            
            # Simple date comparison (normalize formats)
            if gtasks_due and notion_due:
                # Both have dates - compare them
                try:
                    gtasks_date = self.parse_timestamp(gtasks_due)
                    notion_date = self.parse_timestamp(notion_due)
                    if gtasks_date and notion_date:
                        # Compare dates only (ignore time)
                        if gtasks_date.date() != notion_date.date():
                            return True
                except:
                    # If parsing fails, assume they're different
                    return True
            elif gtasks_due or notion_due:
                # One has date, other doesn't
                return True
            
            return False
            
        except Exception as e:
            print(f"Error comparing task content: {e}")
            return True  # Assume different on error to be safe
    
    def _get_change_types(self, gtasks_task, notion_page, gtasks_info):
        """Identify what types of changes occurred between GTasks and Notion"""
        change_types = []
        
        try:
            # Check task name
            gtasks_title = gtasks_task.get('title', '').strip()
            notion_title = notion_page['properties'][NOTION_TASK_NAME]['title'][0]['plain_text'].strip() if notion_page['properties'][NOTION_TASK_NAME]['title'] else ''
            
            if gtasks_title != notion_title:
                change_types.append('title')
            
            # Check task status/completion
            gtasks_status = gtasks_task.get('status', '')
            notion_checkbox = notion_page['properties'][NOTION_STATUS]['checkbox']
            
            gtasks_completed = (gtasks_status == GOOGLE_DONE_STATUS)
            notion_completed = notion_checkbox
            
            if gtasks_completed != notion_completed:
                if gtasks_completed:
                    change_types.append('marked completed')
                else:
                    change_types.append('marked incomplete')
            
            # Check descriptions
            gtasks_description = gtasks_task.get('notes', '').strip()
            notion_description = make_description(notion_page['properties'][NOTION_DESCRIPTION]['rich_text']).strip()
            
            if gtasks_description != notion_description:
                change_types.append('description')
            
            # Check due dates
            gtasks_due = gtasks_task.get('due', '')
            notion_due = ''
            try:
                if notion_page['properties'][NOTION_DATE]['date']:
                    notion_due = notion_page['properties'][NOTION_DATE]['date']['start']
            except:
                pass
            
            if gtasks_due != notion_due:
                change_types.append('due date')
            
            return change_types if change_types else ['unknown changes']
            
        except Exception as e:
            print(f"Error identifying change types: {e}")
            return ['unknown changes']
    
    def execute_bidirectional_sync(self, sync_actions, dry_run=True):
        """Execute the bidirectional sync operations with batch optimization"""
        if dry_run:
            print("=== DRY RUN MODE - NO ACTUAL CHANGES WILL BE MADE ===\n")
        
        changes_made = []
        
        # 1. Update Notion from GTasks (GTasks is newer) - Use parallel processing
        notion_updates = sync_actions['update_notion_from_gtasks']
        if notion_updates:
            print(f"🚀 Batch updating Notion from GTasks: {len(notion_updates)} tasks")
            if dry_run:
                # In dry run, simulate the changes
                for sync_info in notion_updates:
                    changes = self._update_notion_from_gtasks_task(sync_info, dry_run)
                    changes_made.extend(changes)
            else:
                # Use batch parallel processing for Notion updates
                batch_updates = []
                for sync_info in notion_updates:
                    task_data = self._extract_gtasks_data(sync_info['gtasks_task'], sync_info['gtasks_info']['list_id'])
                    batch_updates.append({
                        'page_id': sync_info['notion_page']['id'],
                        'task_data': task_data,
                        'sync_info': sync_info
                    })
                
                # Execute parallel Notion updates
                results = batch_operations_service.parallel_update_notion_pages(batch_updates)
                
                # Process results
                for i, result in enumerate(results):
                    if 'error' not in result:
                        sync_info = batch_updates[i]['sync_info']
                        task_data = batch_updates[i]['task_data']
                        changes_made.append({
                            'action': 'update_notion_from_gtasks',
                            'task_id': sync_info['gtasks_id'],
                            'task_name': task_data['name'],
                            'changes': ['Batch updated from GTasks']
                        })
                        print(f"✅ Batch updated Notion task: {task_data['name']}")
        
        # 2. Update GTasks from Notion (Notion is newer) - Use batch API
        gtasks_updates = sync_actions['update_gtasks_from_notion']
        if gtasks_updates:
            print(f"🚀 Batch updating GTasks from Notion: {len(gtasks_updates)} tasks")
            if dry_run:
                # In dry run, simulate the changes
                for sync_info in gtasks_updates:
                    changes = self._update_gtasks_from_notion_task(sync_info, dry_run)
                    changes_made.extend(changes)
            else:
                # Use batch API for GTasks updates
                batch_updates = []
                for sync_info in gtasks_updates:
                    task_data = self._extract_notion_task_data(sync_info['notion_page'])
                    current_list_id = sync_info['gtasks_info']['list_id']
                    
                    batch_updates.append({
                        'task_data': task_data,
                        'current_list_id': current_list_id,
                        'new_list_id': task_data['gtasks_list_id'],
                        'gtasks_id': sync_info['gtasks_id']
                    })
                
                # Execute batch GTasks updates
                results = batch_operations_service.batch_update_gtasks(batch_updates)
                
                # Process results and update Notion sync timestamps
                for i, result in enumerate(results):
                    if 'error' not in result:
                        sync_info = gtasks_updates[i]
                        task_data = batch_updates[i]['task_data']
                        batch_update_info = batch_updates[i]
                        
                        # Check if this was a category/list change that needs icon update
                        current_list_id = batch_update_info['current_list_id']
                        new_list_id = batch_update_info['new_list_id']
                        
                        if current_list_id != new_list_id:
                            # Category changed - update Notion page icon
                            from src.services.api_connections import notion
                            from src.services.notion_service import notion_service
                            
                            notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
                            new_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
                            
                            notion.pages.update(
                                page_id=sync_info['notion_page']['id'],
                                icon={
                                    'type': 'emoji',
                                    'emoji': new_icon
                                },
                                properties={
                                    NOTION_GTASKS_LIST_ID: {
                                        'rich_text': [{'text': {'content': new_list_id}}]
                                    }
                                }
                            )
                            
                            print(f"🎨 Updated Notion page icon to: {new_icon} (category change in batch operation)")
                            
                            # Record icon update
                            sync_reporter.record_icon_update(task_data['name'], 'previous', new_icon)
                        
                        # Update Notion sync timestamp
                        self.notion_service.update_sync_timestamp(sync_info['notion_page']['id'])
                        
                        changes_made.append({
                            'action': 'update_gtasks_from_notion',
                            'task_id': sync_info['gtasks_id'],
                            'task_name': task_data['name'],
                            'changes': ['Batch updated from Notion']
                        })
                        print(f"✅ Batch updated GTasks task: {task_data['name']}")
        
        # 3. Create new Notion tasks from GTasks - Use parallel processing
        notion_creates = sync_actions['create_notion_from_gtasks']
        if notion_creates:
            print(f"🚀 Batch creating Notion tasks from GTasks: {len(notion_creates)} tasks")
            if dry_run:
                # In dry run, simulate the changes
                for sync_info in notion_creates:
                    changes = self._create_notion_from_gtasks_task(sync_info, dry_run)
                    changes_made.extend(changes)
            else:
                # Use parallel processing for Notion creates
                batch_creates = []
                for sync_info in notion_creates:
                    task_data = self._extract_gtasks_data(sync_info['gtasks_task'], sync_info['gtasks_info']['list_id'])
                    batch_creates.append({
                        'task_data': task_data,
                        'sync_info': sync_info
                    })
                
                # Execute parallel Notion creates
                results = batch_operations_service.parallel_create_notion_pages(batch_creates)
                
                # Process results
                for i, result in enumerate(results):
                    if 'error' not in result:
                        sync_info = batch_creates[i]['sync_info']
                        task_data = batch_creates[i]['task_data']
                        changes_made.append({
                            'action': 'create_notion_from_gtasks',
                            'task_id': sync_info['gtasks_id'],
                            'task_name': task_data['name'],
                            'changes': ['Batch created in Notion']
                        })
                        print(f"✅ Batch created Notion task: {task_data['name']}")
        
        return changes_made
    
    def _update_notion_from_gtasks_task(self, sync_info, dry_run):
        """Update a Notion task with data from GTasks"""
        gtasks_task = sync_info['gtasks_task']
        notion_page = sync_info['notion_page']
        gtasks_info = sync_info['gtasks_info']
        
        changes = []
        
        # Add logging for individual task timestamp-based decision
        print(f"  🔄 Syncing GTasks → Notion for task '{gtasks_task.get('title', 'unnamed')}':")
        print(f"     ⏰ This task's timestamps:")
        print(f"       GTasks updated: {gtasks_task.get('updated', 'unknown')}")
        print(f"       Notion last edited: {notion_page.get('last_edited_time', 'unknown')}")
        print(f"     🔄 Per-task decision: GTasks has newer changes")
        
        # Extract GTasks data
        task_data = self._extract_gtasks_data(gtasks_task, gtasks_info['list_id'])
        
        # Get current Notion data for comparison
        current_notion_name = notion_page['properties'][NOTION_TASK_NAME]['title'][0]['plain_text'] if notion_page['properties'][NOTION_TASK_NAME]['title'] else ''
        current_notion_status = notion_page['properties'][NOTION_STATUS]['checkbox']
        current_notion_category = notion_page['properties'][NOTION_LIST_NAME]['select']['name'] if notion_page['properties'][NOTION_LIST_NAME]['select'] else ''
        
        # Compare and track changes
        if task_data['name'] != current_notion_name:
            changes.append(f"Title: '{current_notion_name}' → '{task_data['name']}'")
        
        notion_status = task_data['gtasks_status'] == 'completed'
        if notion_status != current_notion_status:
            status_text = 'completed' if notion_status else 'pending'
            current_status_text = 'completed' if current_notion_status else 'pending'
            changes.append(f"Status: '{current_status_text}' → '{status_text}'")
        
        if task_data['notion_list_name'] != current_notion_category:
            changes.append(f"Category: '{current_notion_category}' → '{task_data['notion_list_name']}'")
        
        if changes:
            print(f"  🗘️ Updating Notion task: {task_data['name']}")
            for change in changes:
                print(f"    - {change}")
            
            if not dry_run:
                self.notion_service.update_task(
                    task_data['name'],
                    task_data['date'],
                    task_data['description'],
                    task_data['notion_list_name'],
                    notion_page['id'],
                    task_data['gtasks_id'],
                    task_data['gtasks_list_id'],
                    task_data['gtasks_status']
                )
                print(f"    ✅ Successfully updated Notion task")
        
        return [{
            'action': 'update_notion_from_gtasks',
            'task_id': sync_info['gtasks_id'],
            'task_name': task_data['name'],
            'changes': changes
        }] if changes else []
    
    def _update_gtasks_from_notion_task(self, sync_info, dry_run):
        """Update a GTasks task with data from Notion"""
        gtasks_task = sync_info['gtasks_task']
        notion_page = sync_info['notion_page']
        gtasks_info = sync_info['gtasks_info']  # This contains the actual current list info
        
        changes = []
        
        # Extract Notion data
        task_data = self._extract_notion_task_data(notion_page)
        
        # Get current GTasks list ID - where the task actually is in GTasks
        current_gtasks_list_id = gtasks_info['list_id']
        
        # Get stored GTasks list ID from Notion (where Notion thinks it is)
        stored_gtasks_list_id = make_one_line_plain_text(
            notion_page['properties'][NOTION_GTASKS_LIST_ID]['rich_text']
        )
        
        # Add logging for individual task timestamp-based decision
        print(f"  🔄 Syncing Notion → GTasks for task '{gtasks_task.get('title', 'unnamed')}':")
        print(f"     ⏰ This task's timestamps:")
        print(f"       GTasks updated: {gtasks_task.get('updated', 'unknown')}")
        print(f"       Notion last edited: {notion_page.get('last_edited_time', 'unknown')}")
        print(f"     🔄 Per-task decision: Notion has newer changes")
        
        # Compare and track changes
        
        if task_data['name'] != gtasks_task.get('title', ''):
            changes.append(f"Title: '{gtasks_task.get('title', '')}' → '{task_data['name']}'")
        
        if task_data['description'] != gtasks_task.get('notes', ''):
            changes.append(f"Description changed")
        
        if task_data['gtasks_status'] != gtasks_task.get('status'):
            status_text = 'completed' if task_data['gtasks_status'] == 'completed' else 'pending'
            current_status_text = 'completed' if gtasks_task.get('status') == 'completed' else 'pending'
            changes.append(f"Status: '{current_status_text}' → '{status_text}'")
        
        if task_data['gtasks_list_id'] != current_gtasks_list_id:
            changes.append(f"List: moved to '{task_data['notion_list_name']}'")
        
        
        if changes:
            print(f"  🗘️ Updating GTasks task: {task_data['name']}")
            for change in changes:
                print(f"    - {change}")
            
            if not dry_run:
                self.google_tasks_service.update_task(
                    task_data['name'],
                    task_data['description'],
                    task_data['date'],
                    current_gtasks_list_id,
                    task_data['gtasks_list_id'],
                    sync_info['gtasks_id'],
                    task_data['gtasks_status']
                )
                
                # Update Notion with new list ID if task was moved between lists
                if task_data['gtasks_list_id'] != current_gtasks_list_id:
                    # Task was moved to a different list, update the stored list ID and icon in Notion
                    from src.services.api_connections import notion
                    from src.services.notion_service import notion_service
                    
                    # Calculate new icon based on updated category
                    notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
                    new_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
                    
                    notion.pages.update(
                        page_id=notion_page['id'],
                        icon={
                            'type': 'emoji',
                            'emoji': new_icon
                        },
                        properties={
                            NOTION_GTASKS_LIST_ID: {
                                'rich_text': [{'text': {'content': task_data['gtasks_list_id']}}]
                            }
                        }
                    )
                    print(f"    ✅ Updated Notion GTasks List ID: {current_gtasks_list_id} → {task_data['gtasks_list_id']}")
                    print(f"    🎨 Updated Notion page icon to: {new_icon} (for category: {task_data['notion_list_name']})")
                    print(f"    📁 This represents a category change from Notion → GTasks")
                
                # Also update if the stored ID doesn't match actual current location
                elif stored_gtasks_list_id != current_gtasks_list_id:
                    # Stored ID is out of sync, update it and refresh icon
                    from src.services.api_connections import notion
                    from src.services.notion_service import notion_service
                    
                    # Calculate icon based on current category (since this is a correction)
                    notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
                    current_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
                    
                    notion.pages.update(
                        page_id=notion_page['id'],
                        icon={
                            'type': 'emoji',
                            'emoji': current_icon
                        },
                        properties={
                            NOTION_GTASKS_LIST_ID: {
                                'rich_text': [{'text': {'content': current_gtasks_list_id}}]
                            }
                        }
                    )
                    print(f"    ✅ Synced Notion GTasks List ID: {stored_gtasks_list_id} → {current_gtasks_list_id} (corrected mismatch)")
                    print(f"    🎨 Refreshed Notion page icon to: {current_icon} (for category: {task_data['notion_list_name']})")
                
                # Update Notion sync timestamp
                self.notion_service.update_sync_timestamp(notion_page['id'])
                print(f"    ✅ Successfully updated GTasks task and Notion sync timestamp")
        
        return [{
            'action': 'update_gtasks_from_notion',
            'task_id': sync_info['gtasks_id'],
            'task_name': task_data['name'],
            'changes': changes
        }] if changes else []
    
    def _create_notion_from_gtasks_task(self, sync_info, dry_run):
        """Create a new Notion task from GTasks"""
        gtasks_task = sync_info['gtasks_task']
        gtasks_info = sync_info['gtasks_info']
        
        task_data = self._extract_gtasks_data(gtasks_task, gtasks_info['list_id'])
        
        print(f"  Creating Notion task: {task_data['name']} in {task_data['notion_list_name']}")
        
        if not dry_run:
            self.notion_service.create_task(
                task_data['name'],
                task_data['date'],
                task_data['description'],
                task_data['notion_list_name'],
                task_data['gtasks_id'],
                task_data['gtasks_list_id'],
                task_data['gtasks_status']
            )
        
        return [{
            'action': 'create_notion_from_gtasks',
            'task_id': sync_info['gtasks_id'],
            'task_name': task_data['name'],
            'changes': ['Created new task in Notion']
        }]
    
    def _extract_gtasks_data(self, task, gtasks_list_id):
        """Extract data from a Google Task (reuse existing logic)"""
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
        notion_list_name = DEFAULT_LIST_NAME  # fallback
        
        # First, try to find existing mapping
        for category, list_id in self.category_mappings.items():
            if list_id == gtasks_list_id:
                notion_list_name = category
                break
        
        # If no mapping found and we're using default, try to create dynamic mapping
        if notion_list_name == DEFAULT_LIST_NAME and gtasks_list_id != DEFAULT_LIST_ID:
            # Get the GTasks list name from the gtasks_info if available
            gtasks_lists = self.google_tasks_service.get_all_task_lists()
            
            for gtasks_list in gtasks_lists:
                if gtasks_list['id'] == gtasks_list_id:
                    list_title = gtasks_list['title']
                    print(f'🔄 Bidirectional sync: Creating dynamic Notion category for GTasks list "{list_title}"')
                    
                    # Use dynamic category creation
                    if category_manager.ensure_gtasks_list_has_notion_category(list_title, gtasks_list_id, create_if_missing=True):
                        notion_list_name = list_title
                        # Refresh our local mappings cache
                        self.category_mappings = category_manager.get_all_mappings()
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
    
    def _extract_notion_task_data(self, page):
        """Extract task data from a Notion page (reuse existing logic)"""
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
        
        # Get date
        try:
            task_date = parse_datetime_string(
                page['properties'][NOTION_DATE]['date']['start'][:-6], 
                '%Y-%m-%dT%H:%M:%S.000'
            )
        except:
            try:
                from src.utils.date_helpers import parse_date_string
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
            
            if not gtasks_list_id:
                gtasks_list_id = DEFAULT_LIST_ID
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
    
    def _add_date_filters(self, query_filter):
        """Add date filters to Notion query"""
        max_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() + timedelta(weeks=FUTURE_WEEKS_TO_SYNC))
        )
        min_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() - timedelta(weeks=PAST_WEEKS_TO_SYNC))
        )
        
        # Convert single property filter to 'and' structure for date filters
        base_filter = query_filter.copy()
        query_filter.clear()
        query_filter['and'] = [base_filter]
        
        # Always include completed tasks regardless of date to prevent duplicates
        # The key fix: completed tasks must always be included in the query
        if PAST_WEEKS_TO_SYNC >= 0 and FUTURE_WEEKS_TO_SYNC >= 0:
            # Include: completed tasks OR (incomplete tasks within date range) OR (incomplete tasks without dates)
            query_filter['and'].extend([
                {'or': [
                    {'property': NOTION_STATUS, 'checkbox': {'equals': True}},  # All completed tasks
                    {'property': NOTION_DATE, 'date': {'on_or_after': min_date}}
                ]},
                {'or': [
                    {'property': NOTION_STATUS, 'checkbox': {'equals': True}},  # All completed tasks  
                    {'property': NOTION_DATE, 'date': {'on_or_before': max_date}}
                ]}
            ])
        elif PAST_WEEKS_TO_SYNC >= 0:
            query_filter['and'].append({
                'or': [
                    {'property': NOTION_STATUS, 'checkbox': {'equals': True}},  # All completed tasks
                    {'property': NOTION_DATE, 'date': {'on_or_after': min_date}}
                ]
            })
        elif FUTURE_WEEKS_TO_SYNC >= 0:
            query_filter['and'].append({
                'or': [
                    {'property': NOTION_STATUS, 'checkbox': {'equals': True}},  # All completed tasks
                    {'property': NOTION_DATE, 'date': {'on_or_before': max_date}}
                ]
            })
    
    def _get_filtered_gtasks(self, list_id):
        """Get GTasks with date filters applied"""
        max_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() + timedelta(weeks=FUTURE_WEEKS_TO_SYNC))
        )
        min_date = add_timezone_for_notion(
            datetime_to_string(datetime.now() - timedelta(weeks=PAST_WEEKS_TO_SYNC))
        )
        
        if PAST_WEEKS_TO_SYNC >= 0 and FUTURE_WEEKS_TO_SYNC >= 0:
            return self.google_tasks_service.get_tasks_from_list(
                list_id, due_min=min_date, due_max=max_date
            )
        elif PAST_WEEKS_TO_SYNC >= 0:
            return self.google_tasks_service.get_tasks_from_list(
                list_id, due_min=min_date
            )
        elif FUTURE_WEEKS_TO_SYNC >= 0:
            return self.google_tasks_service.get_tasks_from_list(
                list_id, due_max=max_date
            )
        else:
            return self.google_tasks_service.get_tasks_from_list(list_id)


def run_bidirectional_sync(dry_run=True):
    """Main function to run bidirectional sync"""
    print("Starting bidirectional sync with timestamp comparison...\n")
    
    sync_manager = BidirectionalSyncManager()
    
    # Analyze what needs to be synced
    sync_actions = sync_manager.analyze_bidirectional_sync()
    
    # Print summary
    print("=== SYNC ANALYSIS SUMMARY ===")
    print(f"Tasks to update in Notion from GTasks: {len(sync_actions['update_notion_from_gtasks'])}")
    print(f"Tasks to update in GTasks from Notion: {len(sync_actions['update_gtasks_from_notion'])}")
    print(f"New tasks to create in Notion: {len(sync_actions['create_notion_from_gtasks'])}")
    print(f"Tasks already in sync: {len(sync_actions['no_sync_needed'])}")
    print(f"Conflicts requiring attention: {len(sync_actions['conflicts'])}\n")
    
    # Execute sync
    changes = sync_manager.execute_bidirectional_sync(sync_actions, dry_run)
    
    print(f"\n=== SYNC COMPLETE ===")
    print(f"Total changes made: {len([c for c in changes if c['changes']])}")
    
    return sync_actions, changes