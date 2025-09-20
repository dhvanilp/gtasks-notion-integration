"""
Category Manager for handling dynamic category to Google Tasks list mapping
"""
import json
import os
from src.config.settings import PROJECT_LOCATION
from src.services.google_tasks_service import google_tasks_service
from src.services.notion_service import notion_service


class CategoryManager:
    """Manages the mapping between Notion categories and Google Tasks lists"""
    
    def __init__(self):
        self.mapping_file = os.path.join(PROJECT_LOCATION, 'category_list_mapping.json')
        self.category_to_list_id = {}
        self.load_mapping()
    
    def load_mapping(self):
        """Load category to list ID mapping from file"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r') as f:
                    self.category_to_list_id = json.load(f)
                print(f'Loaded category mappings: {self.category_to_list_id}')
            except Exception as e:
                print(f'Error loading category mapping: {e}')
                self.category_to_list_id = {}
        else:
            print('No existing category mapping found, will create new one')
            self.category_to_list_id = {}
    
    def save_mapping(self):
        """Save category to list ID mapping to file"""
        try:
            with open(self.mapping_file, 'w') as f:
                json.dump(self.category_to_list_id, f, indent=2)
            print(f'Saved category mappings to {self.mapping_file}')
        except Exception as e:
            print(f'Error saving category mapping: {e}')
    
    def sync_categories_with_gtasks_lists(self, bidirectional=True):
        """
        Sync Notion categories with Google Tasks lists (bidirectionally)
        - Get all categories from Notion
        - Create Google Tasks lists for new categories
        - Get all Google Tasks lists
        - Create Notion categories for unmapped lists
        - Update mapping
        """
        print('🔄 Syncing categories with Google Tasks lists...')
        changes_made = {'created_gtasks_lists': [], 'created_notion_categories': []}
        
        # Step 1: Notion categories → Google Tasks lists (with cleanup)
        categories = notion_service.get_all_categories()
        if not categories:
            categories = notion_service.get_active_categories_from_tasks()
        
        # Get current GTasks lists to validate existing mappings
        gtasks_lists = google_tasks_service.get_all_task_lists()
        valid_list_ids = {gtasks_list['id']: gtasks_list['title'] for gtasks_list in gtasks_lists}
        
        if categories:
            # Clean up invalid mappings first
            invalid_mappings = []
            for category, list_id in self.category_to_list_id.items():
                if list_id not in valid_list_ids:
                    invalid_mappings.append(category)
                    print(f'⚠️ Invalid mapping found: Category "{category}" mapped to non-existent list ID: {list_id}')
            
            # Remove invalid mappings
            for category in invalid_mappings:
                del self.category_to_list_id[category]
                print(f'🗑️ Removed invalid mapping for category "{category}"')
            
            # Process each Notion category
            new_mappings = {}
            for category in categories:
                if category in self.category_to_list_id:
                    # Category already mapped and valid
                    list_id = self.category_to_list_id[category]
                    new_mappings[category] = list_id
                    print(f'Category "{category}" already mapped to list ID: {list_id} ("{valid_list_ids[list_id]}")')
                else:
                    # Create new Google Tasks list for this category
                    print(f'✨ Creating new Google Tasks list for category: "{category}"')
                    new_list = google_tasks_service.get_or_create_list_for_category(category)
                    
                    if new_list:
                        new_mappings[category] = new_list['id']
                        changes_made['created_gtasks_lists'].append({
                            'category': category,
                            'list_id': new_list['id'],
                            'list_title': new_list['title']
                        })
                        print(f'✅ Mapped category "{category}" to new list ID: {new_list["id"]}')
                    else:
                        print(f'❌ Failed to create list for category: "{category}"')
            
            self.category_to_list_id.update(new_mappings)
        
        # Step 2: Google Tasks lists → Notion categories (if bidirectional)
        if bidirectional:
            print('Checking for unmapped Google Tasks lists...')
            gtasks_lists = google_tasks_service.get_all_task_lists()
            unmapped_lists = notion_service.get_unmapped_categories_from_gtasks_lists(
                gtasks_lists, self.category_to_list_id
            )
            
            if unmapped_lists:
                print(f'Found {len(unmapped_lists)} unmapped Google Tasks lists')
                for gtasks_list in unmapped_lists:
                    list_name = gtasks_list['title']
                    list_id = gtasks_list['id']
                    
                    # Create Notion category option
                    print(f'✨ Creating Notion category for Google Tasks list: "{list_name}"')
                    if notion_service.create_category_option(list_name):
                        # Add to mapping
                        self.category_to_list_id[list_name] = list_id
                        changes_made['created_notion_categories'].append({
                            'category': list_name,
                            'list_id': list_id
                        })
                        print(f'✅ Mapped new category "{list_name}" to existing list ID: {list_id}')
                    else:
                        print(f'❌ Failed to create Notion category for list: "{list_name}"')
            else:
                print('No unmapped Google Tasks lists found')
        
        # Save updated mapping
        self.save_mapping()
        
        # Report changes made
        if changes_made['created_gtasks_lists'] or changes_made['created_notion_categories']:
            print(f'✨ Bidirectional category sync completed:')
            for gtasks_list in changes_made['created_gtasks_lists']:
                print(f'   → Created GTasks list "{gtasks_list["list_title"]}" for Notion category "{gtasks_list["category"]}"')
            for notion_cat in changes_made['created_notion_categories']:
                print(f'   ← Created Notion category "{notion_cat["category"]}" for GTasks list')
        else:
            print('✅ All categories already synchronized')
        
        return self.category_to_list_id
    
    def get_list_id_for_category(self, category):
        """Get Google Tasks list ID for a given category"""
        return self.category_to_list_id.get(category)
    
    def get_all_mappings(self):
        """Get all category to list ID mappings"""
        return self.category_to_list_id.copy()
    
    def refresh_mappings(self):
        """Refresh mappings by syncing with current Notion categories"""
        return self.sync_categories_with_gtasks_lists()
    
    def ensure_category_exists(self, category_name, create_if_missing=True):
        """Ensure a category exists in both systems, create if missing"""
        if not create_if_missing:
            return self.category_to_list_id.get(category_name)
        
        # Check if already mapped
        if category_name in self.category_to_list_id:
            return self.category_to_list_id[category_name]
        
        print(f'🔄 Dynamic category sync: "{category_name}" not found, creating...')
        
        # Create GTasks list for this category
        new_list = google_tasks_service.get_or_create_list_for_category(category_name)
        if new_list:
            self.category_to_list_id[category_name] = new_list['id']
            print(f'✅ Created GTasks list "{new_list["title"]}" for category "{category_name}"')
            
            # Also ensure Notion has this category option
            if notion_service.create_category_option(category_name):
                print(f'✅ Ensured Notion category option "{category_name}" exists')
            
            # Save mapping
            self.save_mapping()
            return new_list['id']
        
        print(f'❌ Failed to create category "{category_name}"')
        return None
    
    def ensure_gtasks_list_has_notion_category(self, gtasks_list_name, gtasks_list_id, create_if_missing=True):
        """Ensure a GTasks list has corresponding Notion category"""
        if not create_if_missing:
            return gtasks_list_name in self.category_to_list_id
        
        # Check if already mapped
        if gtasks_list_name in self.category_to_list_id:
            return True
        
        print(f'🔄 Dynamic category sync: GTasks list "{gtasks_list_name}" needs Notion category...')
        
        # Create Notion category option
        if notion_service.create_category_option(gtasks_list_name):
            self.category_to_list_id[gtasks_list_name] = gtasks_list_id
            print(f'✅ Created Notion category "{gtasks_list_name}" for GTasks list')
            
            # Save mapping
            self.save_mapping()
            return True
        
        print(f'❌ Failed to create Notion category for GTasks list "{gtasks_list_name}"')
        return False


# Global category manager instance
category_manager = CategoryManager()