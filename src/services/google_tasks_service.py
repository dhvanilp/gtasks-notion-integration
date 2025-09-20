"""
Google Tasks service for creating and updating tasks
"""
from datetime import date, datetime

from src.config.settings import *
from src.utils.date_helpers import datetime_to_string, date_to_string, add_timezone_for_notion
from src.services.api_connections import service


class GoogleTasksService:
    """Service for managing Google Tasks operations"""
    
    def create_task(self, task_name, task_description, task_date, gtasks_list_id, task_status):
        """Creates a new Google Task and returns the task"""
        task = {
            'title': task_name,
            'notes': task_description,
            'status': task_status
        }

        # Handle due dates
        if isinstance(task_date, date):
            task_date = datetime.combine(task_date, datetime.min.time())
            task['due'] = add_timezone_for_notion(datetime_to_string(task_date))
        
        print(f'Adding this task to Google Tasks: {task_name}\n')
        new_task = service.tasks().insert(tasklist=gtasks_list_id, body=task).execute()
        return new_task

    def update_task(self, task_name, task_description, task_date, current_list_id, 
                   new_list_id, gtasks_id, task_status):
        """Updates a Google Task and returns the updated task"""
        updated_task = {
            'title': task_name,
            'id': gtasks_id,
            'notes': task_description,
            'status': task_status
        }

        # Handle due dates
        if isinstance(task_date, date):
            task_date = datetime.combine(task_date, datetime.min.time())
            updated_task['due'] = add_timezone_for_notion(datetime_to_string(task_date))
        elif task_date == '':
            # Remove due date if empty
            updated_task['due'] = None

        # Log the update for debugging
        status_str = "completed" if task_status == GOOGLE_DONE_STATUS else "pending"
        print(f'Updating Google Task: {task_name} - Status: {status_str}')

        # Check if task needs to be moved to a different list
        if current_list_id == new_list_id:
            # Same list - just update the task
            print(f'Updating task properties in same list: {current_list_id}')
            updated_task = service.tasks().update(
                tasklist=current_list_id, 
                task=gtasks_id, 
                body=updated_task
            ).execute()
        else:
            # Different list - use move operation to preserve task ID
            print(f'📋 Moving task from list {current_list_id} to {new_list_id}')
            print(f'   This will update the task\'s timestamp in Google Tasks')
            
            # First move the task to the new list (preserves ID and updates timestamp)
            move_result = service.tasks().move(
                tasklist=current_list_id,
                task=gtasks_id,
                destinationTasklist=new_list_id
            ).execute()
            
            # Then update the task properties in the new list
            updated_task = service.tasks().update(
                tasklist=new_list_id, 
                task=gtasks_id, 
                body=updated_task
            ).execute()
            
            print(f'✅ Task moved successfully - ID preserved: {gtasks_id}')
            print(f'   New timestamp: {updated_task.get("updated", "unknown")}')

        return updated_task

    def delete_task(self, gtasks_list_id, gtasks_id):
        """Deletes a Google Task"""
        try:
            service.tasks().delete(tasklist=gtasks_list_id, task=gtasks_id).execute()
            return True
        except Exception as e:
            print(f'Could not delete task from Google Tasks: {e}\n')
            return False

    def get_task(self, gtasks_list_id, gtasks_id):
        """Gets a single Google Task"""
        try:
            return service.tasks().get(tasklist=gtasks_list_id, task=gtasks_id).execute()
        except:
            return {'status': 'deleted'}

    def get_tasks_from_list(self, gtasks_list_id, max_results=500, show_deleted=False, 
                           due_min=None, due_max=None):
        """Gets tasks from a specific Google Tasks list"""
        params = {
            'tasklist': gtasks_list_id,
            'maxResults': max_results,
            'showHidden': True,
            'showDeleted': show_deleted
        }
        
        if due_min:
            params['dueMin'] = due_min
        if due_max:
            params['dueMax'] = due_max
            
        result = service.tasks().list(**params).execute()
        
        # Filter out tasks with deleted: true, unless explicitly requesting deleted tasks
        if not show_deleted and 'items' in result:
            original_count = len(result['items'])
            result['items'] = [task for task in result['items'] if not task.get('deleted', False)]
            filtered_count = len(result['items'])
            
            if original_count != filtered_count:
                print(f"  Filtered out {original_count - filtered_count} deleted tasks from list")
        
        return result

    def get_all_task_lists(self):
        """Gets all Google Tasks lists"""
        try:
            results = service.tasklists().list().execute()
            return results.get('items', [])
        except Exception as e:
            print(f'Error getting task lists: {e}')
            return []

    def create_task_list(self, list_name):
        """Creates a new Google Tasks list and returns the list"""
        try:
            list_body = {'title': list_name}
            new_list = service.tasklists().insert(body=list_body).execute()
            print(f'Created new Google Tasks list: {list_name}')
            return new_list
        except Exception as e:
            print(f'Error creating task list {list_name}: {e}')
            return None

    def get_or_create_list_for_category(self, category_name):
        """Gets existing list or creates new one for a category"""
        # Get all existing lists
        all_lists = self.get_all_task_lists()
        
        # Check if list already exists for this category
        for task_list in all_lists:
            if task_list['title'] == category_name:
                return task_list
        
        # Create new list if it doesn't exist
        return self.create_task_list(category_name)


# Global service instance
google_tasks_service = GoogleTasksService()