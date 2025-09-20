"""
Notion service for creating and updating tasks
"""
from datetime import date

from src.config.settings import *
from src.utils.date_helpers import now_to_datetime_string, add_timezone_for_notion, date_to_string
from src.services.api_connections import notion


class NotionService:
    """Service for managing Notion operations"""
    
    def create_task(self, task_name, task_date, task_description, notion_list, 
                   gtasks_id, gtasks_list_id, gtasks_status):
        """Creates a new Notion task and returns the task"""
        notion_status = self._convert_gtasks_status_to_notion(gtasks_status)

        new_task = notion.pages.create(
            parent={'database_id': NOTION_DATABASE_ID},
            icon={
                'type': 'emoji',
                'emoji': self._get_task_icon(notion_status, notion_list)
            },
            properties={
                NOTION_TASK_NAME: {
                    'title': [{'text': {'content': task_name}}]
                },
                NOTION_LIST_NAME: {
                    'select': {'name': notion_list}
                },
                NOTION_STATUS: {
                    'checkbox': notion_status
                },
                NOTION_DESCRIPTION: {
                    'rich_text': [{'text': {'content': task_description}}]
                },
                NOTION_GTASKS_TASK_ID: {
                    'rich_text': [{'text': {'content': gtasks_id}}]
                },
                NOTION_GTASKS_LIST_ID: {
                    'rich_text': [{'text': {'content': gtasks_list_id}}]
                },
                NOTION_LAST_SYNCED: {
                    'date': {
                        'start': add_timezone_for_notion(now_to_datetime_string()),
                        'end': None
                    }
                }
            }
        )
        
        # Handle due date if present
        if isinstance(task_date, date):
            notion.pages.update(
                page_id=new_task['id'],
                properties={
                    NOTION_DATE: {
                        'date': {
                            'start': date_to_string(task_date),
                            'end': None
                        }
                    }
                }
            )

        print(f'Adding this task to Notion: {task_name}\n')
        return new_task

    def update_task(self, task_name, task_date, task_description, notion_list, 
                   notion_page_id, gtasks_id, gtasks_list_id, gtasks_status):
        """Updates a Notion task and returns the updated task"""
        notion_status = self._convert_gtasks_status_to_notion(gtasks_status)

        # Log status conversion for debugging
        status_str = "completed" if notion_status else "not completed"
        print(f'Updating Notion task: {task_name}')
        print(f'  Status: {status_str}, Category: {notion_list}')
        
        # Get current task info for change detection
        current_page = notion.pages.retrieve(page_id=notion_page_id)
        current_category = current_page['properties'][NOTION_LIST_NAME]['select']['name'] if current_page['properties'][NOTION_LIST_NAME]['select'] else ''
        
        if current_category != notion_list:
            print(f'  📁 Category change: "{current_category}" → "{notion_list}"')

        updated_task = notion.pages.update(
            page_id=notion_page_id,
            icon={
                'type': 'emoji',
                'emoji': self._get_task_icon(notion_status, notion_list)
            },
            properties={
                NOTION_TASK_NAME: {
                    'title': [{'text': {'content': task_name}}]
                },
                NOTION_LIST_NAME: {
                    'select': {'name': notion_list}
                },
                NOTION_STATUS: {
                    'checkbox': notion_status
                },
                NOTION_DESCRIPTION: {
                    'rich_text': [{'text': {'content': task_description}}]
                },
                NOTION_GTASKS_TASK_ID: {
                    'rich_text': [{'text': {'content': gtasks_id}}]
                },
                NOTION_GTASKS_LIST_ID: {
                    'rich_text': [{'text': {'content': gtasks_list_id}}]
                },
                NOTION_LAST_SYNCED: {
                    'date': {
                        'start': add_timezone_for_notion(now_to_datetime_string()),
                        'end': None
                    }
                }
            }
        )

        # Handle due date
        if isinstance(task_date, date):
            notion.pages.update(
                page_id=updated_task['id'],
                properties={
                    NOTION_DATE: {
                        'date': {
                            'start': date_to_string(task_date),
                            'end': None
                        }
                    }
                }
            )
        else:
            notion.pages.update(
                page_id=updated_task['id'],
                properties={
                    NOTION_DATE: {'date': None}
                }
            )

        print(f'✅ Updated Notion task: {task_name}\n')
        return updated_task


    def update_sync_timestamp(self, page_id):
        """Update the last synced timestamp for a task"""
        return notion.pages.update(
            page_id=page_id,
            properties={
                NOTION_LAST_SYNCED: {
                    'date': {
                        'start': add_timezone_for_notion(now_to_datetime_string()),
                        'end': None
                    }
                }
            }
        )

    def query_database(self, filter_conditions, start_cursor=None):
        """Query the Notion database with given filters"""
        query_params = {
            'database_id': NOTION_DATABASE_ID,
            'filter': filter_conditions
        }
        
        if start_cursor:
            query_params['start_cursor'] = start_cursor
            
        return notion.databases.query(**query_params)

    def get_all_categories(self):
        """Get all unique categories from the Notion database"""
        try:
            # Get the database to extract select options from the Category field
            database_response = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
            
            # Extract categories from the select field options
            category_property = database_response['properties'].get(NOTION_LIST_NAME, {})
            if category_property.get('type') == 'select':
                select_options = category_property.get('select', {}).get('options', [])
                categories = [option['name'] for option in select_options]
                print(f'Found categories in Notion database: {categories}')
                return categories
            else:
                print(f'Category field ({NOTION_LIST_NAME}) is not a select field')
                return []
                
        except Exception as e:
            print(f'Error getting categories from Notion: {e}')
            return []

    def get_active_categories_from_tasks(self):
        """Get unique categories from actual tasks in the database"""
        try:
            # Query all tasks
            filter_conditions = {}
            
            response = self.query_database(filter_conditions)
            categories = set()
            
            # Process all pages
            while True:
                for page in response.get('results', []):
                    category_property = page.get('properties', {}).get(NOTION_LIST_NAME, {})
                    if category_property.get('type') == 'select' and category_property.get('select'):
                        category_name = category_property['select']['name']
                        categories.add(category_name)
                
                # Check if there are more pages
                if response.get('has_more'):
                    response = self.query_database(filter_conditions, start_cursor=response.get('next_cursor'))
                else:
                    break
            
            categories_list = list(categories)
            print(f'Found active categories from tasks: {categories_list}')
            return categories_list
            
        except Exception as e:
            print(f'Error getting active categories from tasks: {e}')
            return []

    def create_category_option(self, category_name):
        """Add a new category option to the Category select field in Notion database"""
        try:
            # Get current database properties
            database_response = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
            
            # Get current category property
            category_property = database_response['properties'].get(NOTION_LIST_NAME, {})
            
            if category_property.get('type') != 'select':
                print(f'Category field ({NOTION_LIST_NAME}) is not a select field')
                return False
            
            # Get current select options
            current_options = category_property.get('select', {}).get('options', [])
            
            # Check if category already exists
            for option in current_options:
                if option['name'] == category_name:
                    print(f'Category "{category_name}" already exists')
                    return True
            
            # Add new option
            new_option = {
                'name': category_name,
                'color': 'default'  # Notion will auto-assign a color
            }
            
            updated_options = current_options + [new_option]
            
            # Update database schema
            update_response = notion.databases.update(
                database_id=NOTION_DATABASE_ID,
                properties={
                    NOTION_LIST_NAME: {
                        'select': {
                            'options': updated_options
                        }
                    }
                }
            )
            
            print(f'Created new Notion category option: "{category_name}"')
            return True
            
        except Exception as e:
            print(f'Error creating category option "{category_name}": {e}')
            return False

    def get_unmapped_categories_from_gtasks_lists(self, gtasks_lists, current_mappings):
        """Find Google Tasks lists that don't have corresponding Notion categories"""
        unmapped_lists = []
        mapped_list_ids = set(current_mappings.values())
        
        for gtasks_list in gtasks_lists:
            list_id = gtasks_list['id']
            list_name = gtasks_list['title']
            
            # Skip if this list is already mapped
            if list_id in mapped_list_ids:
                continue
                
            # Skip default system lists that we don't want to sync
            if list_name.lower() in ['my tasks', 'tasks']:
                continue
                
            unmapped_lists.append(gtasks_list)
        
        return unmapped_lists

    def _convert_gtasks_status_to_notion(self, gtasks_status):
        """Convert Google Tasks status to Notion checkbox status"""
        if gtasks_status == GOOGLE_TO_DO_STATUS:
            return NOTION_CHECKBOX_NOT_COMPLETED
        else:
            return NOTION_CHECKBOX_COMPLETED

    def _get_task_icon(self, notion_status, notion_list):
        """Get appropriate emoji icon based on task status and category"""
        # If task is completed, always show checkmark
        if notion_status:
            return '✅'
        
        # For incomplete tasks, show icon based on category
        category_icons = {
            'Finance💰': '💰',
            'Mind 🧠': '🧠', 
            'Misc 📋': '📋',
            'Career 👨‍💻': '👨‍💻',
            'Health 🏋️‍♂️': '🏋️‍♂️',
            'Google Tasks ✓': '📝',
            'List': '📝'  # Default list
        }
        
        # Return category-specific icon or default
        return category_icons.get(notion_list, '📝')


# Global service instance
notion_service = NotionService()