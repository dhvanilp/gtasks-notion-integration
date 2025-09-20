"""
Enhanced sync reporting and logging utilities
"""
from datetime import datetime
from typing import Dict, List, Any
import json


class SyncReporter:
    """Enhanced reporting for sync operations with detailed tables and step-by-step logging"""
    
    def __init__(self):
        self.sync_start_time = None
        self.sync_data = {
            'timestamp': None,
            'duration': None,
            'steps': [],
            'summary': {
                'notion_to_gtasks': {
                    'created': 0,
                    'updated': 0,
                    'failed': 0,
                    'tasks': []
                },
                'gtasks_to_notion': {
                    'created': 0,
                    'updated': 0,
                    'failed': 0,
                    'tasks': []
                },
                'bidirectional': {
                    'notion_newer': 0,
                    'gtasks_newer': 0,
                    'conflicts': 0,
                    'no_change': 0,
                    'tasks': []
                },
                'categories': {
                    'synced': 0,
                    'created_notion': 0,
                    'created_gtasks': 0,
                    'mappings': {}
                },
                'icons': {
                    'updated': 0,
                    'tasks': []
                },
                'errors': []
            }
        }
    
    def start_sync(self):
        """Mark the start of sync operation"""
        self.sync_start_time = datetime.now()
        self.sync_data['timestamp'] = self.sync_start_time.strftime('%Y-%m-%d %H:%M:%S')
        
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🚀 ENHANCED GTASKS-NOTION SYNC STARTED" + " " * 18 + "║")
        print("║" + f" Started at: {self.sync_data['timestamp']}" + " " * (78 - 12 - len(self.sync_data['timestamp'])) + "║")
        print("╚" + "═" * 78 + "╝")
        print()
    
    def log_step(self, step_number: int, title: str, description: str = ""):
        """Log a sync step with enhanced formatting"""
        step_info = {
            'number': step_number,
            'title': title,
            'description': description,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        self.sync_data['steps'].append(step_info)
        
        print(f"┌─ Step {step_number}: {title}")
        if description:
            print(f"│  {description}")
        print(f"│  ⏰ {step_info['timestamp']}")
        print("└" + "─" * 50)
        print()
    
    def log_substep(self, action: str, details: str = "", status: str = "info"):
        """Log a substep with status indicators"""
        status_icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'processing': '🔄'
        }
        
        icon = status_icons.get(status, 'ℹ️')
        print(f"  {icon}  {action}")
        if details:
            print(f"      └─ {details}")
    
    def log_batch_operation(self, operation_type: str, count: int, duration: float = None):
        """Log batch operation details"""
        duration_text = f" ({duration:.1f}s)" if duration else ""
        print(f"  🚀  Batch {operation_type}: {count} items{duration_text}")
        
        if count > 0:
            batch_size = 3 if operation_type.startswith('Notion') else count
            batches = (count + batch_size - 1) // batch_size
            if batches > 1:
                print(f"      └─ Processing in {batches} batches of {batch_size} items each")
    
    def record_notion_to_gtasks(self, action: str, task_name: str, details: Dict[str, Any]):
        """Record Notion to GTasks sync action"""
        record = {
            'action': action,
            'task_name': task_name,
            'details': details,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        if action == 'created':
            self.sync_data['summary']['notion_to_gtasks']['created'] += 1
        elif action == 'updated':
            self.sync_data['summary']['notion_to_gtasks']['updated'] += 1
        elif action == 'failed':
            self.sync_data['summary']['notion_to_gtasks']['failed'] += 1
        
        self.sync_data['summary']['notion_to_gtasks']['tasks'].append(record)
    
    def record_gtasks_to_notion(self, action: str, task_name: str, details: Dict[str, Any]):
        """Record GTasks to Notion sync action"""
        record = {
            'action': action,
            'task_name': task_name,
            'details': details,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        if action == 'created':
            self.sync_data['summary']['gtasks_to_notion']['created'] += 1
        elif action == 'updated':
            self.sync_data['summary']['gtasks_to_notion']['updated'] += 1
        elif action == 'failed':
            self.sync_data['summary']['gtasks_to_notion']['failed'] += 1
        
        self.sync_data['summary']['gtasks_to_notion']['tasks'].append(record)
    
    def record_bidirectional_sync(self, action: str, task_name: str, comparison: str, changes: List[str]):
        """Record bidirectional sync action"""
        record = {
            'action': action,
            'task_name': task_name,
            'comparison': comparison,
            'changes': changes,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        if comparison == 'notion_newer':
            self.sync_data['summary']['bidirectional']['notion_newer'] += 1
        elif comparison == 'gtasks_newer':
            self.sync_data['summary']['bidirectional']['gtasks_newer'] += 1
        elif comparison == 'conflict':
            self.sync_data['summary']['bidirectional']['conflicts'] += 1
        else:
            self.sync_data['summary']['bidirectional']['no_change'] += 1
        
        self.sync_data['summary']['bidirectional']['tasks'].append(record)
    
    def record_category_sync(self, category_mappings: Dict[str, str]):
        """Record category synchronization results"""
        self.sync_data['summary']['categories']['mappings'] = category_mappings
        self.sync_data['summary']['categories']['synced'] = len(category_mappings)
    
    def record_icon_update(self, task_name: str, old_icon: str, new_icon: str):
        """Record icon update"""
        record = {
            'task_name': task_name,
            'old_icon': old_icon or 'none',
            'new_icon': new_icon,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        self.sync_data['summary']['icons']['updated'] += 1
        self.sync_data['summary']['icons']['tasks'].append(record)
    
    def record_error(self, error_type: str, message: str, details: Dict[str, Any] = None):
        """Record error information"""
        error_record = {
            'type': error_type,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        self.sync_data['summary']['errors'].append(error_record)
    
    def end_sync(self, success: bool = True):
        """Complete sync and show comprehensive summary"""
        end_time = datetime.now()
        duration = end_time - self.sync_start_time
        self.sync_data['duration'] = duration.total_seconds()
        
        print("\n")
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 25 + "📊 SYNC COMPLETION SUMMARY" + " " * 25 + "║")
        print("╚" + "═" * 78 + "╝")
        
        # Basic info
        status = "✅ COMPLETED SUCCESSFULLY" if success else "❌ COMPLETED WITH ERRORS"
        print(f"\n🏁 Status: {status}")
        print(f"⏱️  Duration: {duration.total_seconds():.1f} seconds")
        print(f"📅 Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Summary tables
        self._print_summary_tables()
        
        # Detailed breakdown
        if success:
            self._print_detailed_breakdown()
        
        print("\n" + "═" * 80)
        print("🎉 Sync operation completed. All systems synchronized!")
        print("═" * 80 + "\n")
    
    def _print_summary_tables(self):
        """Print comprehensive summary tables"""
        print(f"\n┌─ 📋 OPERATION SUMMARY")
        print("│")
        
        # Notion to GTasks table
        n2g = self.sync_data['summary']['notion_to_gtasks']
        print("│  🔵 Notion → Google Tasks:")
        print(f"│     Created: {n2g['created']:>3} | Updated: {n2g['updated']:>3} | Failed: {n2g['failed']:>3}")
        
        # GTasks to Notion table  
        g2n = self.sync_data['summary']['gtasks_to_notion']
        print("│  🟢 Google Tasks → Notion:")
        print(f"│     Created: {g2n['created']:>3} | Updated: {g2n['updated']:>3} | Failed: {g2n['failed']:>3}")
        
        # Bidirectional sync table
        bid = self.sync_data['summary']['bidirectional']
        print("│  🔄 Bidirectional Updates:")
        print(f"│     Notion Newer: {bid['notion_newer']:>3} | GTasks Newer: {bid['gtasks_newer']:>3}")
        print(f"│     No Changes: {bid['no_change']:>5} | Conflicts: {bid['conflicts']:>7}")
        
        # Categories and icons
        cat = self.sync_data['summary']['categories']
        icons = self.sync_data['summary']['icons']
        print(f"│  🗂️  Categories Synced: {cat['synced']}")
        print(f"│  🎨 Icons Updated: {icons['updated']}")
        
        # Errors
        errors = len(self.sync_data['summary']['errors'])
        print(f"│  ❌ Errors: {errors}")
        print("└" + "─" * 50)
    
    def _print_detailed_breakdown(self):
        """Print detailed breakdown of all operations"""
        print(f"\n┌─ 📊 DETAILED BREAKDOWN")
        print("│")
        
        # Category mappings
        if self.sync_data['summary']['categories']['mappings']:
            print("│  🗂️  Category Mappings:")
            for category, list_id in self.sync_data['summary']['categories']['mappings'].items():
                print(f"│     '{category}' ↔ {list_id[:8]}...")
        
        # Recent changes
        all_tasks = []
        
        # Collect all task operations
        for task in self.sync_data['summary']['notion_to_gtasks']['tasks']:
            all_tasks.append({
                'type': f"Notion→GTasks ({task['action']})",
                'name': task['task_name'],
                'time': task['timestamp'],
                'details': task.get('details', {})
            })
        
        for task in self.sync_data['summary']['gtasks_to_notion']['tasks']:
            all_tasks.append({
                'type': f"GTasks→Notion ({task['action']})",
                'name': task['task_name'], 
                'time': task['timestamp'],
                'details': task.get('details', {})
            })
        
        for task in self.sync_data['summary']['bidirectional']['tasks']:
            direction = "Notion→GTasks" if task['comparison'] == 'notion_newer' else "GTasks→Notion"
            all_tasks.append({
                'type': f"Bidirectional ({direction})",
                'name': task['task_name'],
                'time': task['timestamp'],
                'details': {'changes': task['changes']}
            })
        
        # Show recent task changes
        if all_tasks:
            print("│")
            print("│  📝 Task Operations:")
            for task in sorted(all_tasks, key=lambda x: x['time'])[-10:]:  # Last 10 operations
                print(f"│     {task['time']} | {task['type']:<20} | {task['name'][:30]}")
                if task['details'].get('changes'):
                    for change in task['details']['changes'][:2]:  # First 2 changes
                        print(f"│                      └─ {change}")
        
        # Icon updates
        if self.sync_data['summary']['icons']['tasks']:
            print("│")
            print("│  🎨 Icon Updates:")
            for icon_update in self.sync_data['summary']['icons']['tasks'][-5:]:  # Last 5
                print(f"│     {icon_update['time']} | {icon_update['task_name'][:30]} | {icon_update['old_icon']} → {icon_update['new_icon']}")
        
        # Errors
        if self.sync_data['summary']['errors']:
            print("│")
            print("│  ❌ Errors:")
            for error in self.sync_data['summary']['errors']:
                print(f"│     {error['time']} | {error['type']}: {error['message']}")
        
        print("└" + "─" * 60)
    
    def get_sync_data(self):
        """Get complete sync data for external use"""
        return self.sync_data
    
    def save_sync_report(self, file_path: str):
        """Save detailed sync report to file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.sync_data, f, indent=2, default=str)
            print(f"📄 Detailed sync report saved to: {file_path}")
        except Exception as e:
            print(f"❌ Failed to save sync report: {e}")


# Global reporter instance
sync_reporter = SyncReporter()