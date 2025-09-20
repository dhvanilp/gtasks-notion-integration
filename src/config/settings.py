"""Configuration settings for Google Tasks and Notion integration

This module loads configuration from config.yaml to keep sensitive data
out of the source code.
"""

import os
import yaml
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / 'config.yaml'

# Load configuration from YAML file
def load_config():
    """Load configuration from config.yaml file"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}\n"
            f"Please copy config.yaml.example to config.yaml and configure your settings."
        )
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

# Load the configuration
config = load_config()

#####################
### PATHS SETUP ####
#####################

# Project location - Docker vs local
PROJECT_LOCATION = ('/app/' if config['project']['docker_env'] or os.environ.get('DOCKER_ENV') 
                   else config['project']['local_path'])

# ----------------------------------------- NOTION SETUP ------------------------------------------

NOTION_TOKEN = config['notion']['token']
NOTION_DATABASE_ID = config['notion']['database_id']
NOTION_PAGE_URL_ROOT = config['notion']['page_url_root']

# ------------------------------------- GOOGLE TASKS SETUP -------------------------------------

TIMEZONE = config['timezone']['name']
TIMEZONE_OFFSET_FROM_GMT = config['timezone']['offset_from_gmt']

# Sync time ranges (in weeks)
PAST_WEEKS_TO_SYNC = config['sync']['past_weeks']
FUTURE_WEEKS_TO_SYNC = config['sync']['future_weeks']

# ------------------------------------ MULTIPLE LIST SETUP ------------------------------------

DEFAULT_LIST_NAME = config['default_list']['name']
DEFAULT_LIST_ID = config['default_list']['id']

# Google Tasks Lists to sync with Notion Calendar database
# Format: 'Notion Calendar Name' : 'Google Tasks List ID'
LIST_DICTIONARY = {
    DEFAULT_LIST_NAME: DEFAULT_LIST_ID,
}

# ------------------------------------- NOTION DATABASE SETUP -------------------------------------

# Basic task fields
NOTION_TASK_NAME = config['notion_fields']['task_name']
NOTION_STATUS = config['notion_fields']['status']
NOTION_LIST_NAME = config['notion_fields']['category']
NOTION_DATE = config['notion_fields']['due_date']
NOTION_DESCRIPTION = config['notion_fields']['description']

# Integration fields
NOTION_GTASKS_TASK_ID = config['notion_fields']['gtasks_task_id']
NOTION_GTASKS_LIST_ID = config['notion_fields']['gtasks_list_id']
NOTION_LAST_SYNCED = config['notion_fields']['last_synced']

# Notion task statuses (Done field is now checkbox - True = completed, False = not completed)
NOTION_CHECKBOX_COMPLETED = True
NOTION_CHECKBOX_NOT_COMPLETED = False

# ------------------------------ ADDITIONAL CONSTANTS -----------------------------

# Google Tasks statuses
GOOGLE_TO_DO_STATUS = 'needsAction'
GOOGLE_DONE_STATUS = 'completed'