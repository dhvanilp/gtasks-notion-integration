#!/usr/bin/env python3
"""
Script to update icons for all existing Notion pages with the new icon system
"""
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.services.notion_service import notion_service
from src.services.api_connections import notion
from src.config.settings import *


class PageIconUpdater:
    """Updates icons for all existing Notion pages"""
    
    def __init__(self):
        # Rate limit: ~3 requests per second
        self.rate_limit = Semaphore(3)
        self.delay = 1.0  # 1 second between batches
    
    def get_all_existing_pages(self):
        """Get all existing pages in the Notion database"""
        print("🔍 Fetching all existing Notion pages...")
        
        all_pages = []
        has_more = True
        next_cursor = None
        
        while has_more:
            # Use direct Notion API call without filters to get all pages
            query_params = {
                'database_id': NOTION_DATABASE_ID
            }
            
            if next_cursor:
                query_params['start_cursor'] = next_cursor
            
            response = notion.databases.query(**query_params)
            
            all_pages.extend(response['results'])
            has_more = response['has_more']
            next_cursor = response.get('next_cursor')
            
            print(f"  Retrieved {len(response['results'])} pages (total: {len(all_pages)})")
            
            if not has_more or not next_cursor:
                break
        
        print(f"✅ Found {len(all_pages)} total pages to update")
        return all_pages
    
    def extract_page_data(self, page):
        """Extract relevant data from a Notion page"""
        try:
            # Get task name
            task_name = ''
            if page['properties'].get(NOTION_TASK_NAME, {}).get('title'):
                task_name = page['properties'][NOTION_TASK_NAME]['title'][0]['plain_text']
            
            # Get completion status
            notion_status = page['properties'].get(NOTION_STATUS, {}).get('checkbox', False)
            
            # Get category/list
            notion_list = ''
            if page['properties'].get(NOTION_LIST_NAME, {}).get('select'):
                notion_list = page['properties'][NOTION_LIST_NAME]['select']['name']
            
            return {
                'page_id': page['id'],
                'task_name': task_name,
                'notion_status': notion_status,
                'notion_list': notion_list,
                'current_icon': page.get('icon', {})
            }
        except Exception as e:
            print(f"❌ Error extracting data from page: {e}")
            return None
    
    def update_single_page_icon(self, page_data):
        """Update icon for a single page"""
        with self.rate_limit:
            try:
                # Get appropriate icon using the same logic as the service
                task_icon = notion_service._get_task_icon(
                    page_data['notion_status'], 
                    page_data['notion_list']
                )
                
                # Check if icon needs updating
                current_icon = page_data['current_icon']
                current_emoji = None
                if current_icon and current_icon.get('type') == 'emoji':
                    current_emoji = current_icon.get('emoji')
                
                if current_emoji == task_icon:
                    print(f"  ⏭️  Skipping '{page_data['task_name']}' - icon already correct ({task_icon})")
                    return {'skipped': True, 'page_id': page_data['page_id']}
                
                # Update the page icon
                notion.pages.update(
                    page_id=page_data['page_id'],
                    icon={
                        'type': 'emoji',
                        'emoji': task_icon
                    }
                )
                
                status = '✅' if page_data['notion_status'] else '⏳'
                print(f"  {status} Updated '{page_data['task_name']}' → {task_icon} ({page_data['notion_list']})")
                
                return {
                    'success': True, 
                    'page_id': page_data['page_id'],
                    'task_name': page_data['task_name'],
                    'icon': task_icon,
                    'old_icon': current_emoji
                }
                
            except Exception as e:
                print(f"  ❌ Failed to update '{page_data['task_name']}': {e}")
                return {
                    'error': str(e), 
                    'page_id': page_data['page_id'],
                    'task_name': page_data['task_name']
                }
    
    def update_all_page_icons(self, dry_run=False):
        """Update icons for all existing pages"""
        if dry_run:
            print("🔍 DRY RUN MODE - No actual changes will be made\n")
        
        # Get all existing pages
        all_pages = self.get_all_existing_pages()
        
        if not all_pages:
            print("No pages found to update")
            return
        
        # Extract page data
        print("\n📊 Analyzing pages...")
        page_data_list = []
        for page in all_pages:
            page_data = self.extract_page_data(page)
            if page_data:
                page_data_list.append(page_data)
        
        print(f"✅ Processed {len(page_data_list)} pages for icon updates")
        
        # Show preview of changes
        print(f"\n🎨 Icon assignment preview:")
        icon_counts = {}
        for page_data in page_data_list:
            task_icon = notion_service._get_task_icon(
                page_data['notion_status'], 
                page_data['notion_list']
            )
            icon_counts[task_icon] = icon_counts.get(task_icon, 0) + 1
        
        for icon, count in sorted(icon_counts.items()):
            print(f"  {icon} → {count} pages")
        
        if dry_run:
            print(f"\n🔍 DRY RUN COMPLETE - Would update {len(page_data_list)} pages")
            return
        
        # Confirm before proceeding
        print(f"\n⚠️  About to update {len(page_data_list)} page icons")
        response = input("Do you want to proceed? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled")
            return
        
        # Update icons in parallel batches
        print(f"\n🚀 Updating {len(page_data_list)} page icons...")
        
        # Split into batches of 3 (rate limit)
        batch_size = 3
        batches = [page_data_list[i:i + batch_size] for i in range(0, len(page_data_list), batch_size)]
        
        all_results = []
        successful_updates = 0
        skipped_updates = 0
        failed_updates = 0
        
        for batch_num, batch in enumerate(batches):
            print(f"\n📦 Processing batch {batch_num + 1}/{len(batches)} ({len(batch)} pages)...")
            
            # Use ThreadPoolExecutor for parallel execution within batch
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                
                for page_data in batch:
                    future = executor.submit(self.update_single_page_icon, page_data)
                    futures.append(future)
                
                # Collect results
                batch_results = []
                for future in futures:
                    try:
                        result = future.result()
                        batch_results.append(result)
                        
                        if result.get('success'):
                            successful_updates += 1
                        elif result.get('skipped'):
                            skipped_updates += 1
                        else:
                            failed_updates += 1
                            
                    except Exception as e:
                        print(f"  ❌ Batch operation failed: {e}")
                        batch_results.append({'error': str(e)})
                        failed_updates += 1
                
                all_results.extend(batch_results)
            
            # Rate limit delay between batches
            if batch_num < len(batches) - 1:
                print(f"  ⏱️  Rate limit delay ({self.delay}s)...")
                time.sleep(self.delay)
        
        # Summary
        print(f"\n" + "="*70)
        print(f"🎉 Icon Update Complete!")
        print(f"✅ Successfully updated: {successful_updates} pages")
        print(f"⏭️  Skipped (already correct): {skipped_updates} pages")
        print(f"❌ Failed: {failed_updates} pages")
        print(f"📊 Total processed: {len(page_data_list)} pages")
        print(f"=" * 70 + "\n")
        
        # Show any failures
        if failed_updates > 0:
            print("❌ Failed updates:")
            for result in all_results:
                if result.get('error'):
                    print(f"  • {result.get('task_name', 'Unknown')}: {result['error']}")
        
        return all_results


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update icons for all existing Notion pages')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be updated without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print("🎨 Notion Page Icon Updater")
    print("=" * 50)
    
    try:
        # Initialize services
        print("🔌 Initializing Notion connection...")
        
        # Test connection
        database_response = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        print(f"✅ Connected to database: {database_response.get('title', [{}])[0].get('plain_text', 'Unknown')}")
        
        # Create updater and run
        updater = PageIconUpdater()
        
        if args.force and not args.dry_run:
            # Skip confirmation for automation
            updater.update_all_page_icons(dry_run=False)
        else:
            updater.update_all_page_icons(dry_run=args.dry_run)
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()