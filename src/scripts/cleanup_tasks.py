#!/usr/bin/env python3
"""
Convenience script to clean up orphaned tasks
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    from utilities.cleanup_orphaned_tasks import main
    main()