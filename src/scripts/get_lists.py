#!/usr/bin/env python3
"""
Convenience script to get Google Tasks list IDs
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    from utilities.get_gtasks_lists import get_gtasks_lists
    
    try:
        get_gtasks_lists()
    except FileNotFoundError:
        print("❌ client_secret.json not found!")
        print("Please download your OAuth credentials from Google Cloud Console")
        print("and save as 'client_secret.json' in this directory.")
    except Exception as e:
        print(f"❌ Error: {e}")