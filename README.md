# 🧠 Smart Google Tasks ↔ Notion Integration

## 🎯 Overview

**Intelligent bidirectional synchronization** with timestamp-based conflict resolution between Google Tasks and Notion. This integration automatically determines which system has the latest changes and syncs accordingly.

**🚀 Smart Sync Features:**
- 🧠 **Timestamp-based conflict resolution** - Automatically syncs the newest changes
- 🔄 **Intelligent bidirectional updates** - No more sync conflicts
- 📝 **Task movement tracking** - Handles category/list changes seamlessly
- ⚡ **Enhanced performance** - Only syncs what actually changed
- 🔒 **Secure configuration** - All sensitive data externalized to YAML
- 🐳 **Docker support** - Production-ready containerized deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (or Docker)
- Google account with Google Tasks
- Notion account with workspace access

### 1. **Installation**

#### Option A: Local Setup
```bash
# Clone repository
git clone https://github.com/dhvanilp/gtasks-notion-integration
cd gtasks-notion-integration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure application
cp config.yaml.example config.yaml
# Edit config.yaml with your credentials
```

#### Option B: Docker Setup
```bash
# Clone repository
git clone https://github.com/dhvanilp/gtasks-notion-integration
cd gtasks-notion-integration

# Configure for Docker
cp config.docker.yaml config.yaml
# Edit config.yaml with your credentials

# Run with Docker
docker-compose up -d
```

### 2. **Configuration**

Create your `config.yaml` from the template:
```yaml
# Notion Configuration
notion:
  token: "your_notion_integration_token_here"
  database_id: "your_notion_database_id_here"
  
# Timezone Settings
timezone:
  name: "America/New_York" 
  offset_from_gmt: "-05:00"
```

See [SETUP.md](SETUP.md) for detailed configuration guide.

### 3. **Run Smart Sync**

```bash
# Preview what would be synced (recommended first run)
python main.py --dry-run

# Run actual sync
python main.py

# With verbose output
python main.py --verbose
```

## 📁 Project Structure

```
├── main.py                        # 🎯 Main smart sync entry point
├── config.yaml.example            # 📝 Configuration template
├── config.docker.yaml             # 🐳 Docker configuration template
├── src/
│   ├── config/
│   │   └── settings.py            # ⚙️ YAML configuration loader
│   ├── services/
│   │   ├── api_connections.py     # 🔌 Google/Notion API connections
│   │   ├── google_tasks_service.py# 📋 Google Tasks operations
│   │   ├── notion_service.py      # 📝 Notion operations
│   │   └── category_manager.py    # 🗂️ Category/list management
│   ├── sync_operations/
│   │   ├── smart_sync.py          # 🧠 Main smart sync orchestrator
│   │   ├── bidirectional_sync.py  # 🔄 Timestamp comparison logic
│   │   ├── gtasks_to_notion.py    # ➡️ Google Tasks → Notion sync
│   │   └── notion_to_gtasks.py    # ⬅️ Notion → Google Tasks sync
│   ├── utils/
│   │   ├── date_helpers.py        # 📅 Date/time utilities
│   │   ├── notion_helpers.py      # 📝 Notion formatting utilities
│   │   └── sync_reporter.py       # 📊 Sync reporting and logging
│   ├── utilities/
│   │   ├── manage_categories.py   # 🗂️ Category management
│   │   ├── dump_google_tasks.py   # 📥 Export Google Tasks data
│   │   └── cleanup_orphaned_tasks.py # 🧹 Cleanup utilities
│   └── setup/
│       ├── setup_notion.py        # 🔧 Initial Notion setup  
│       └── setup_notion_database.py # 🗃️ Add database properties
├── docker-compose.yml             # 🐳 Docker orchestration
├── Dockerfile                     # 🐳 Container definition
├── requirements.txt               # 📦 Python dependencies
├── SETUP.md                       # 📚 Detailed setup guide
└── DOCKER.md                     # 🐳 Docker deployment guide
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
3. **Category sync**: Manage category/list mappings automatically
4. **Update timestamps**: Record sync completion

## 🔧 Configuration

The application uses YAML configuration files to keep sensitive data secure:

- **`config.yaml`** - Your actual configuration (gitignored)
- **`config.yaml.example`** - Template for local development  
- **`config.docker.yaml`** - Template for Docker deployment

### Key Configuration Sections:
- **notion**: API credentials and database settings
- **google_tasks**: OAuth credentials and file paths
- **timezone**: Timezone settings for proper date handling
- **sync**: Sync range and behavior settings

## 🐳 Docker Deployment

For production deployment, use Docker:

```bash
# Start the service (runs every 10 minutes)
docker-compose up -d

# View logs
docker-compose logs -f gtasks-notion-sync

# Stop the service
docker-compose down
```

See [DOCKER.md](DOCKER.md) for complete Docker deployment guide.

## 🛠️ Utility Scripts

### Available Scripts
```bash
# Get Google Tasks list IDs
python src/scripts/get_lists.py

# Manage category mappings  
python src/utilities/manage_categories.py

# Clean up orphaned tasks
python src/utilities/cleanup_orphaned_tasks.py

# Setup Notion database properties
python src/setup/setup_notion_database.py

# Export Google Tasks data
python src/utilities/dump_google_tasks.py
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
| **GTasks Task ID** | Rich text | Google Task ID |
| **GTasks List ID** | Rich text | Google List ID |
| **Last Synced** | Date | Last sync timestamp |

## 🔒 Security Features

- **No hardcoded secrets**: All sensitive data in gitignored YAML files
- **Template-based config**: Safe examples with placeholder values  
- **Docker secrets**: Secure volume-mounted configuration
- **OAuth token storage**: Secure token persistence

## 🎯 Smart Sync Features

### **Intelligent Updates**
- ✅ Automatically detects which system has newer changes
- ✅ Handles task movements between categories/lists
- ✅ Preserves Google Tasks IDs when tasks move
- ✅ Only syncs fields that actually changed

### **Performance Optimizations**
- ⚡ Pagination support for large datasets
- ⚡ Batched API operations
- ⚡ Change detection to avoid unnecessary updates
- ⚡ Efficient timestamp comparison

## 🔧 Troubleshooting

### Common Issues

1. **Configuration file not found**
   ```bash
   # Copy and edit the configuration template
   cp config.yaml.example config.yaml
   # Edit with your actual credentials
   ```

2. **"Could not find property" in Notion**
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

### Debug Mode
```bash
# Verbose output for troubleshooting
python main.py --dry-run --verbose
```

For more detailed troubleshooting, see [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md).

## 🚀 Automation Setup

### Cron Job (Linux/Mac)
```bash
# Every 15 minutes
*/15 * * * * cd /path/to/gtasks-notion-integration && /path/to/venv/bin/python main.py

# Every hour  
0 * * * * cd /path/to/gtasks-notion-integration && /path/to/venv/bin/python main.py
```

### Docker (Recommended)
```bash
# Automated sync every 10 minutes
docker-compose up -d
```

### Task Scheduler (Windows)
- Create basic task
- Set trigger (e.g., every 15 minutes)
- Action: Start program `python.exe` with arguments `main.py`
- Start in: `C:\path\to\gtasks-notion-integration`

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Detailed configuration guide
- **[DOCKER.md](DOCKER.md)** - Docker deployment guide
- **[DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)** - Troubleshooting help

## 🎉 Usage Examples

```bash
# Basic smart sync
python main.py

# Preview changes without making them
python main.py --dry-run

# Verbose output for debugging
python main.py --verbose

# Setup utilities
python src/scripts/get_lists.py
python src/utilities/manage_categories.py
python src/setup/setup_notion_database.py
```

---

**🧠 Ready for smart syncing?** 

1. Configure your `config.yaml` file
2. Run `python main.py --dry-run` to preview changes
3. Run `python main.py` to start intelligent synchronization!

For production deployment, see the Docker setup in [DOCKER.md](DOCKER.md).