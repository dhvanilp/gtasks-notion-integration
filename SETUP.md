# Configuration Setup

This project uses a YAML configuration file to keep sensitive data out of the source code.

## Initial Setup

1. **Copy the example configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Edit `config.yaml` with your actual values:**
   - **Notion Token**: Get from https://www.notion.so/my-integrations
   - **Notion Database ID**: Extract from your database URL
   - **Google Tasks credentials**: Place `client_secret.json` in project root
   - **Timezone**: Set your local timezone
   - **Project path**: Update local path if different

## Configuration Structure

```yaml
# Notion Configuration
notion:
  token: "your_notion_integration_token_here"
  database_id: "your_notion_database_id_here"
  page_url_root: "https://www.notion.so/your-workspace/"

# Google Tasks Configuration
google_tasks:
  client_secret_file: "client_secret.json"
  token_file: "token.pkl"

# Timezone Settings
timezone:
  name: "Asia/Kolkata"
  offset_from_gmt: "+05:30"

# Sync Settings
sync:
  past_weeks: 4
  future_weeks: 10
```

## Security Notes

- `config.yaml` is gitignored and will not be committed to version control
- Keep your `config.yaml` file secure and never share it publicly
- The example file shows the structure but contains placeholder values
- All sensitive data is now externalized from the source code

## Running the Application

After configuring `config.yaml`:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the sync
python main.py
```