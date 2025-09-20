#!/usr/bin/env python3
"""
Enhanced Main Sync Script for Google Tasks and Notion Integration

This script provides seamless bidirectional synchronization:
- ✅ Category synchronization (Notion ↔ Google Tasks)
- ✅ Task completion sync (Done checkbox ↔ completed status) 
- ✅ Seamless deletion sync (automatic detection)
- ✅ Import new tasks in both directions
- ✅ Update tasks when changed in either system

New Features:
- Automatic category/list management
- Enhanced status synchronization
- Improved deletion detection
- Better error handling and logging
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sync_operations.smart_sync import run_smart_sync
from src.services.category_manager import category_manager


def main():
    """Smart bidirectional sync with timestamp comparison"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Tasks + Notion Smart Sync')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be synced without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🧠 Smart Google Tasks + Notion Sync")
    print("="*70 + "\n")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("-" * 70 + "\n")

    try:
        # Initialize API connections
        print("🔌 Initializing API connections...")
        from src.services.api_connections import api
        print("✅ API connections established!\n")

        # Initialize and sync category mappings
        print("🗂️  Synchronizing category mappings...")
        category_manager.sync_categories_with_gtasks_lists(bidirectional=True)
        print("✅ Category mappings synchronized!\n")

        # Run smart bidirectional sync
        print("🚀 Running Smart Bidirectional Sync with Timestamp Comparison")
        print("-" * 70 + "\n")
        
        sync_actions, changes = run_smart_sync(dry_run=args.dry_run)
        
        print("\n" + "="*70)
        print("🎉 Smart Bidirectional Sync completed successfully!")
        print("\n✨ Smart sync features:")
        print("   • Timestamp-based conflict resolution: ACTIVE")
        print("   • Bidirectional updates: INTELLIGENT")
        print("   • Category synchronization: ENHANCED")
        print("   • Task completion sync: SMART")
        print("   • Enhanced error handling: ACTIVE")
        print("="*70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⏹️  Sync interrupted by user")
        print("="*70 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Sync failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        print("\n💡 Troubleshooting tips:")
        print("   • Check your internet connection")
        print("   • Verify API credentials are valid")
        print("   • Run with --verbose for detailed error info")
        print("   • Check if Notion database fields are properly configured")
        print("="*70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()