"""
Batch operations service for optimizing API calls
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore
import time
from typing import List, Dict, Any

from src.services.api_connections import service, notion
from src.config.settings import *


class BatchOperationsService:
    """Service for optimizing API calls using batch operations and parallel processing"""
    
    def __init__(self):
        # Notion rate limit: ~3 requests per second
        self.notion_rate_limit = Semaphore(3)
        self.notion_delay = 1.0  # 1 second between batches
        
    def batch_update_gtasks(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch update multiple Google Tasks using the batch API
        
        Args:
            updates: List of update dictionaries containing:
                - task_data: task content to update
                - current_list_id: current list ID
                - new_list_id: target list ID (if moving)
                - gtasks_id: task ID
        
        Returns:
            List of updated task results
        """
        if not updates:
            return []
        
        print(f"🚀 Batch updating {len(updates)} Google Tasks...")
        
        # Create batch request
        batch_request = service.new_batch_http_request()
        update_results = []
        
        def add_update_result(request_id, response, exception):
            """Callback to handle batch response"""
            if exception:
                print(f"❌ Batch update failed for request {request_id}: {exception}")
                update_results.append({'error': str(exception), 'request_id': request_id})
            else:
                print(f"✅ Batch update successful for request {request_id}")
                update_results.append(response)
        
        # Add all updates to batch
        for i, update in enumerate(updates):
            task_data = update['task_data']
            current_list_id = update['current_list_id']
            new_list_id = update['new_list_id']
            gtasks_id = update['gtasks_id']
            
            # Prepare task body
            updated_task = {
                'title': task_data['name'],
                'id': gtasks_id,
                'notes': task_data['description'],
                'status': task_data['gtasks_status']
            }
            
            # Handle due dates
            if task_data['date']:
                from datetime import date, datetime
                from src.utils.date_helpers import datetime_to_string, add_timezone_for_notion
                
                if isinstance(task_data['date'], date):
                    task_date = datetime.combine(task_data['date'], datetime.min.time())
                    updated_task['due'] = add_timezone_for_notion(datetime_to_string(task_date))
            elif task_data['date'] == '':
                updated_task['due'] = None
            
            # Check if task needs to be moved between lists
            if current_list_id != new_list_id:
                # For moves, we need two operations: move then update
                # First, move the task
                move_request = service.tasks().move(
                    tasklist=current_list_id,
                    task=gtasks_id,
                    destinationTasklist=new_list_id
                )
                batch_request.add(move_request, callback=add_update_result, request_id=f"move_{i}")
                
                # Then update properties in new list
                update_request = service.tasks().update(
                    tasklist=new_list_id,
                    task=gtasks_id,
                    body=updated_task
                )
                batch_request.add(update_request, callback=add_update_result, request_id=f"update_{i}")
            else:
                # Same list - just update
                update_request = service.tasks().update(
                    tasklist=current_list_id,
                    task=gtasks_id,
                    body=updated_task
                )
                batch_request.add(update_request, callback=add_update_result, request_id=f"update_{i}")
        
        # Execute batch request
        try:
            batch_request.execute()
            print(f"✅ Batch update completed for {len(updates)} Google Tasks")
        except Exception as e:
            print(f"❌ Batch request failed: {e}")
            return []
        
        return update_results
    
    def batch_create_gtasks(self, creates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Batch create multiple Google Tasks using the batch API
        
        Args:
            creates: List of create dictionaries containing task data
        
        Returns:
            List of created task results
        """
        if not creates:
            return []
        
        print(f"🚀 Batch creating {len(creates)} Google Tasks...")
        
        batch_request = service.new_batch_http_request()
        create_results = []
        
        def add_create_result(request_id, response, exception):
            """Callback to handle batch response"""
            if exception:
                print(f"❌ Batch create failed for request {request_id}: {exception}")
                create_results.append({'error': str(exception), 'request_id': request_id})
            else:
                print(f"✅ Batch create successful for request {request_id}")
                create_results.append(response)
        
        # Add all creates to batch
        for i, create_data in enumerate(creates):
            task_data = create_data['task_data']
            gtasks_list_id = create_data['gtasks_list_id']
            
            # Prepare task body
            task = {
                'title': task_data['name'],
                'notes': task_data['description'],
                'status': task_data['gtasks_status']
            }
            
            # Handle due dates
            if task_data['date']:
                from datetime import date, datetime
                from src.utils.date_helpers import datetime_to_string, add_timezone_for_notion
                
                if isinstance(task_data['date'], date):
                    task_date = datetime.combine(task_data['date'], datetime.min.time())
                    task['due'] = add_timezone_for_notion(datetime_to_string(task_date))
            
            create_request = service.tasks().insert(tasklist=gtasks_list_id, body=task)
            batch_request.add(create_request, callback=add_create_result, request_id=f"create_{i}")
        
        # Execute batch request
        try:
            batch_request.execute()
            print(f"✅ Batch create completed for {len(creates)} Google Tasks")
        except Exception as e:
            print(f"❌ Batch request failed: {e}")
            return []
        
        return create_results
    
    def parallel_update_notion_pages(self, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Update multiple Notion pages in parallel (respecting rate limits)
        
        Args:
            updates: List of update dictionaries containing:
                - page_id: Notion page ID
                - task_data: task content to update
        
        Returns:
            List of updated page results
        """
        if not updates:
            return []
        
        print(f"🚀 Parallel updating {len(updates)} Notion pages...")
        
        # Split updates into batches of 3 (rate limit)
        batch_size = 3
        batches = [updates[i:i + batch_size] for i in range(0, len(updates), batch_size)]
        all_results = []
        
        for batch_num, batch in enumerate(batches):
            print(f"  Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} pages)...")
            
            # Use ThreadPoolExecutor for parallel execution within batch
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                
                for update in batch:
                    future = executor.submit(self._update_single_notion_page, update)
                    futures.append(future)
                
                # Collect results
                batch_results = []
                for future in futures:
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        print(f"❌ Notion page update failed: {e}")
                        batch_results.append({'error': str(e)})
                
                all_results.extend(batch_results)
            
            # Rate limit delay between batches
            if batch_num < len(batches) - 1:
                time.sleep(self.notion_delay)
        
        print(f"✅ Parallel Notion updates completed for {len(updates)} pages")
        return all_results
    
    def parallel_create_notion_pages(self, creates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple Notion pages in parallel (respecting rate limits)
        
        Args:
            creates: List of create dictionaries containing task data
        
        Returns:
            List of created page results
        """
        if not creates:
            return []
        
        print(f"🚀 Parallel creating {len(creates)} Notion pages...")
        
        # Split creates into batches of 3 (rate limit)
        batch_size = 3
        batches = [creates[i:i + batch_size] for i in range(0, len(creates), batch_size)]
        all_results = []
        
        for batch_num, batch in enumerate(batches):
            print(f"  Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} pages)...")
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                
                for create_data in batch:
                    future = executor.submit(self._create_single_notion_page, create_data)
                    futures.append(future)
                
                # Collect results
                batch_results = []
                for future in futures:
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        print(f"❌ Notion page create failed: {e}")
                        batch_results.append({'error': str(e)})
                
                all_results.extend(batch_results)
            
            # Rate limit delay between batches
            if batch_num < len(batches) - 1:
                time.sleep(self.notion_delay)
        
        print(f"✅ Parallel Notion creates completed for {len(creates)} pages")
        return all_results
    
    def _update_single_notion_page(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Update a single Notion page"""
        page_id = update['page_id']
        task_data = update['task_data']
        
        # Acquire rate limit semaphore
        with self.notion_rate_limit:
            try:
                # Convert GTasks status to Notion checkbox
                notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
                
                # Get appropriate icon
                from src.services.notion_service import notion_service
                task_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
                
                # Prepare properties
                properties = {
                    NOTION_TASK_NAME: {
                        'title': [{'text': {'content': task_data['name']}}]
                    },
                    NOTION_LIST_NAME: {
                        'select': {'name': task_data['notion_list_name']}
                    },
                    NOTION_STATUS: {
                        'checkbox': notion_status
                    },
                    NOTION_DESCRIPTION: {
                        'rich_text': [{'text': {'content': task_data['description']}}]
                    },
                    NOTION_GTASKS_TASK_ID: {
                        'rich_text': [{'text': {'content': task_data['gtasks_id']}}]
                    },
                    NOTION_GTASKS_LIST_ID: {
                        'rich_text': [{'text': {'content': task_data['gtasks_list_id']}}]
                    }
                }
                
                # Handle due date
                if task_data['date']:
                    from src.utils.date_helpers import date_to_string
                    from datetime import date
                    
                    if isinstance(task_data['date'], date):
                        properties[NOTION_DATE] = {
                            'date': {
                                'start': date_to_string(task_data['date']),
                                'end': None
                            }
                        }
                else:
                    properties[NOTION_DATE] = {'date': None}
                
                # Update page with icon and properties
                result = notion.pages.update(
                    page_id=page_id, 
                    icon={
                        'type': 'emoji',
                        'emoji': task_icon
                    },
                    properties=properties
                )
                return result
                
            except Exception as e:
                raise Exception(f"Failed to update Notion page {page_id}: {e}")
    
    def _create_single_notion_page(self, create_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single Notion page"""
        task_data = create_data['task_data']
        
        # Acquire rate limit semaphore
        with self.notion_rate_limit:
            try:
                # Convert GTasks status to Notion checkbox
                notion_status = task_data['gtasks_status'] == GOOGLE_DONE_STATUS
                
                # Get appropriate icon
                from src.services.notion_service import notion_service
                task_icon = notion_service._get_task_icon(notion_status, task_data['notion_list_name'])
                
                # Prepare properties
                properties = {
                    NOTION_TASK_NAME: {
                        'title': [{'text': {'content': task_data['name']}}]
                    },
                    NOTION_LIST_NAME: {
                        'select': {'name': task_data['notion_list_name']}
                    },
                    NOTION_STATUS: {
                        'checkbox': notion_status
                    },
                    NOTION_DESCRIPTION: {
                        'rich_text': [{'text': {'content': task_data['description']}}]
                    },
                    NOTION_GTASKS_TASK_ID: {
                        'rich_text': [{'text': {'content': task_data['gtasks_id']}}]
                    },
                    NOTION_GTASKS_LIST_ID: {
                        'rich_text': [{'text': {'content': task_data['gtasks_list_id']}}]
                    }
                }
                
                # Create page with icon
                new_page = notion.pages.create(
                    parent={'database_id': NOTION_DATABASE_ID},
                    icon={
                        'type': 'emoji',
                        'emoji': task_icon
                    },
                    properties=properties
                )
                
                # Handle due date in separate update if needed
                if task_data['date']:
                    from src.utils.date_helpers import date_to_string
                    from datetime import date
                    
                    if isinstance(task_data['date'], date):
                        notion.pages.update(
                            page_id=new_page['id'],
                            properties={
                                NOTION_DATE: {
                                    'date': {
                                        'start': date_to_string(task_data['date']),
                                        'end': None
                                    }
                                }
                            }
                        )
                
                return new_page
                
            except Exception as e:
                raise Exception(f"Failed to create Notion page: {e}")


# Global batch operations service instance
batch_operations_service = BatchOperationsService()