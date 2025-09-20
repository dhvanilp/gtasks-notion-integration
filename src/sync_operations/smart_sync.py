"""
Smart bidirectional sync that compares timestamps and syncs accordingly
"""
from src.sync_operations.bidirectional_sync import run_bidirectional_sync
from src.sync_operations.gtasks_to_notion import import_new_gtasks
from src.sync_operations.notion_to_gtasks import import_new_notion_tasks
from src.utils.sync_reporter import sync_reporter


def run_smart_sync(dry_run=True):
    """
    Run a complete smart sync that:
    1. Handles new tasks in both directions
    2. Uses timestamp comparison to sync updates bidirectionally
    """
    # Initialize enhanced reporting
    sync_reporter.start_sync()
    
    if dry_run:
        sync_reporter.log_substep("🔍 DRY RUN MODE", "No actual changes will be made", "warning")
        print()
    
    try:
        # Step 1: Import new tasks from both systems
        sync_reporter.log_step(1, "Importing New Tasks", "Creating missing tasks in both directions")
        
        sync_reporter.log_substep("Processing GTasks → Notion", "Looking for new Google Tasks", "processing")
        import_new_gtasks()  # GTasks → Notion (new tasks)
        
        sync_reporter.log_substep("Processing Notion → GTasks", "Looking for Notion tasks without GTasks IDs", "processing")
        import_new_notion_tasks()  # Notion → GTasks (new tasks)
        
        # Step 2: Category synchronization
        sync_reporter.log_step(2, "Category Synchronization", "Ensuring category/list mappings are up to date")
        from src.services.category_manager import category_manager
        category_mappings = category_manager.get_all_mappings()
        sync_reporter.record_category_sync(category_mappings)
        sync_reporter.log_substep(f"Categories synchronized", f"{len(category_mappings)} active mappings", "success")
        
        # Step 3: Run bidirectional sync with timestamp comparison
        sync_reporter.log_step(3, "Bidirectional Timestamp Sync", "Comparing timestamps and syncing changes")
        sync_actions, changes = run_bidirectional_sync(dry_run=dry_run)
        
        # Record sync results
        for change in changes:
            if change.get('changes'):
                if 'notion_from_gtasks' in change['action']:
                    sync_reporter.record_gtasks_to_notion('updated', change['task_name'], {
                        'changes': change['changes']
                    })
                elif 'gtasks_from_notion' in change['action']:
                    sync_reporter.record_notion_to_gtasks('updated', change['task_name'], {
                        'changes': change['changes']
                    })
        
        # Complete reporting
        sync_reporter.end_sync(success=True)
        
        return sync_actions, changes
        
    except Exception as e:
        sync_reporter.record_error("sync_error", str(e))
        sync_reporter.end_sync(success=False)
        print(f"\n❌ Error during smart sync: {e}")
        raise


def run_full_sync():
    """Run a full sync without dry run"""
    return run_smart_sync(dry_run=False)


def preview_sync():
    """Preview what changes would be made without executing them"""
    print("Previewing sync changes...\n")
    return run_smart_sync(dry_run=True)


if __name__ == "__main__":
    # Run preview by default for safety
    preview_sync()