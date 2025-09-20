# 🧠 Smart Google Tasks ↔ Notion Integration

## 🎯 Overview

**Intelligent bidirectional synchronization** with timestamp-based conflict resolution between Google Tasks and Notion. This integration automatically determines which system has the latest changes and syncs accordingly.

**🚀 Smart Sync Features:**
- 🧠 **Timestamp-based conflict resolution** - Automatically syncs the newest changes
- 🔄 **Intelligent bidirectional updates** - No more sync conflicts
- 📝 **Task movement tracking** - Handles category/list changes seamlessly
- ⚡ **Enhanced performance** - Only syncs what actually changed
- 🔒 **Preserves task IDs** - Google Tasks IDs remain stable across list changes
- 🎯 **Clean architecture** - Modern, maintainable codebase

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- Google account with Google Tasks
- Notion account with workspace access

### 1. **Installation**

```bash
# Clone repository
git clone https://github.com/yourusername/gtasks-notion-integration
cd gtasks-notion-integration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. **Google Tasks Setup**

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or use existing
   - Enable **Google Tasks API** (APIs & Services → Library)

2. **Create OAuth Credentials:**
   - Go to APIs & Services → Credentials
   - Create OAuth client ID → Desktop application
   - Download JSON and save as `client_secret.json` in project root

3. **Get your Google Tasks list IDs:**
   ```bash
   python src/scripts/get_lists.py
   ```

### 3. **Notion Setup**

1. **Create Integration:**
   - Go to [Notion Developers](https://www.notion.so/my-integrations)
   - Create new integration
   - Copy the **Integration Token** (starts with `secret_`)

2. **Create Tasks Database:**
   - Create a new database in Notion
   - Share it with your integration
   - Get Database ID from URL: `https://notion.so/workspace/DATABASE_ID?v=...`

3. **Setup database properties:**
   ```bash
   python src/setup/setup_notion_database.py
   ```
   This will automatically add all required fields to your database.

### 4. **Configuration**

Edit `src/config/settings.py`:
```python
# Notion Setup
NOTION_TOKEN = 'secret_your_token_here'
NOTION_DATABASE_ID = 'your_database_id'

# Google Tasks Setup  
TIMEZONE = 'America/New_York'
TIMEZONE_OFFSET_FROM_GMT = '-05:00'

# Optional: Customize sync range
PAST_WEEKS_TO_SYNC = 1
FUTURE_WEEKS_TO_SYNC = 10
```

### 5. **Run Smart Sync**

```bash
# Preview what would be synced (recommended first run)
python main.py --dry-run

# Run actual sync
python main.py

# Set up automation (every 15 minutes)
*/15 * * * * cd /path/to/project && python main.py
```

## 📁 Project Structure

```
├── main.py                        # 🎯 Main smart sync entry point
├── src/
│   ├── config/
│   │   └── settings.py            # ⚙️ Configuration settings
│   ├── services/
│   │   ├── api_connections.py     # 🔌 Google/Notion API connections
│   │   ├── google_tasks_service.py# 📋 Google Tasks operations
│   │   ├── notion_service.py      # 📝 Notion operations
│   │   └── category_manager.py    # 🗂️ Category/list management
│   ├── sync_operations/
│   │   ├── smart_sync.py          # 🧠 Main smart sync orchestrator
│   │   ├── bidirectional_sync.py  # 🔄 Timestamp comparison logic
│   │   ├── gtasks_to_notion.py    # ➡️ Google Tasks → Notion sync
│   │   ├── notion_to_gtasks.py    # ⬅️ Notion → Google Tasks sync
│   │   └── deletion_sync.py       # 🗑️ Deletion handling
│   ├── utils/
│   │   ├── date_helpers.py        # 📅 Date/time utilities
│   │   └── notion_helpers.py      # 📝 Notion formatting utilities
│   ├── utilities/
│   │   ├── get_gtasks_lists.py    # 🔍 List Google Tasks lists
│   │   ├── manage_categories.py   # 🗂️ Category management
│   │   └── cleanup_orphaned_tasks.py # 🧹 Cleanup utilities
│   ├── scripts/
│   │   ├── get_lists.py           # 📋 Get Google Tasks list IDs
│   │   ├── manage_categories.py   # 🗂️ Manage category mappings
│   │   └── cleanup_tasks.py       # 🧹 Clean up orphaned tasks
│   └── setup/
│       ├── setup_notion.py        # 🔧 Initial Notion setup
│       └── setup_notion_database.py # 🗃️ Add database properties
├── requirements.txt               # 📦 Python dependencies
└── README.md                     # 📖 This file
```

## 🧠 How Smart Sync Works

### **Timestamp-Based Conflict Resolution**
1. **Compare timestamps**: GTasks `updated` vs Notion `last_synced`
2. **Determine winner**: Update the system with older data
3. **Sync intelligently**: Only change what needs changing
4. **Track movements**: Handle tasks moving between lists/categories

### **Sync Process**
1. **Import new tasks**: Create tasks that exist in only one system
2. **Bidirectional updates**: Sync changes based on timestamps
3. **Handle deletions**: Sync deleted tasks in both directions
4. **Update timestamps**: Record sync completion

## ⚙️ Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `NOTION_TOKEN` | Notion integration token | Required |
| `NOTION_DATABASE_ID` | Notion database ID | Required |
| `TIMEZONE` | Your timezone | `'Asia/Kolkata'` |
| `TIMEZONE_OFFSET_FROM_GMT` | GMT offset | `'+05:30'` |
| `PAST_WEEKS_TO_SYNC` | Historical sync range | `1` |
| `FUTURE_WEEKS_TO_SYNC` | Future sync range | `10` |
| `SYNC_DELETED_TASKS` | Enable deletion sync | `True` |

## 🛠️ Utility Scripts

### Available Scripts
```bash
# Get Google Tasks list IDs
python src/scripts/get_lists.py

# Manage category mappings
python src/scripts/manage_categories.py

# Clean up orphaned tasks
python src/scripts/cleanup_tasks.py

# Setup Notion database properties
python src/setup/setup_notion_database.py
```

## 📊 Database Properties

The Notion database requires these properties (auto-created by setup script):

| Property Name | Type | Purpose |
|---------------|------|---------|
| **Name** | Title | Task title |
| **Done** | Checkbox | Completion status |
| **Category** | Select | List/category |
| **Due Date** | Date | Due date |
| **Description** | Rich text | Task notes |
| **Synced** | Checkbox | Sync status |
| **Deleted** | Checkbox | Deletion marker |
| **Needs GTasks Update** | Checkbox | Update flag |
| **GTasks Task ID** | Rich text | Google Task ID |
| **GTasks List ID** | Rich text | Google List ID |
| **Last Synced** | Date | Last sync timestamp |

## 🎯 Smart Sync Features

### **Intelligent Updates**
- ✅ Automatically detects which system has newer changes
- ✅ Handles task movements between categories/lists
- ✅ Preserves Google Tasks IDs when tasks move
- ✅ Only syncs fields that actually changed

### **Conflict Resolution**
- 🧠 **GTasks newer**: Updates Notion with GTasks changes
- 🧠 **Notion newer**: Updates GTasks with Notion changes  
- 🧠 **Same timestamp**: No action needed
- 🧠 **Unknown/error**: Flags for manual review

### **Performance Optimizations**
- ⚡ Pagination support for large datasets
- ⚡ Batched API operations
- ⚡ Change detection to avoid unnecessary updates
- ⚡ Efficient timestamp comparison

## 🔧 Troubleshooting

### Common Issues
1. **"client_secret.json not found"**
   ```bash
   # Download OAuth credentials from Google Cloud Console
   # Save as client_secret.json in project root
   ```

2. **"Could not find property"**
   ```bash
   # Run database setup to add missing properties
   python src/setup/setup_notion_database.py
   ```

3. **Import errors**
   ```bash
   # Ensure you're in project root directory
   # Activate virtual environment
   source venv/bin/activate
   ```

4. **Sync conflicts**
   ```bash
   # Run in dry-run mode to preview changes
   python main.py --dry-run
   ```

### Debug Mode
```bash
# Verbose output for troubleshooting
python main.py --dry-run --verbose
```

## 📈 Performance & Scalability

- **Large databases**: Handles thousands of tasks efficiently
- **Rate limiting**: Respects API rate limits automatically
- **Memory efficient**: Processes data in batches
- **Reliable syncing**: Robust error handling and recovery

## 🚀 Automation Setup

### Cron Job (Linux/Mac)
```bash
# Every 15 minutes
*/15 * * * * cd /path/to/gtasks-notion-integration && /path/to/venv/bin/python main.py

# Every hour
0 * * * * cd /path/to/gtasks-notion-integration && /path/to/venv/bin/python main.py
```

### Task Scheduler (Windows)
- Create basic task
- Set trigger (e.g., every 15 minutes)
- Action: Start program `python.exe` with arguments `main.py`
- Start in: `C:\path\to\gtasks-notion-integration`

## 📋 Migration from Legacy Version

If upgrading from an older version:
1. Backup your existing configuration
2. Run `python src/setup/setup_notion_database.py` to add new fields
3. The smart sync will automatically handle existing data

## 🎉 Usage Examples

```bash
# Basic smart sync
python main.py

# Preview changes without making them
python main.py --dry-run

# Get help with commands
python main.py --help

# Setup utilities
python src/scripts/get_lists.py
python src/scripts/manage_categories.py
python src/setup/setup_notion_database.py
```

---

**🧠 Ready for smart syncing?** Run `python main.py --dry-run` to see what would be synced, then `python main.py` to start intelligent synchronization!