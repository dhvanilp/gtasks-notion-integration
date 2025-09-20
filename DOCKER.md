# Docker Deployment Guide

This guide will help you run the GTasks-Notion Integration using Docker for easy deployment and management.

## Quick Start

1. **Prepare configuration files:**
   ```bash
   # Copy the Docker-specific config template
   cp config.docker.yaml config.yaml
   
   # Edit with your actual values
   nano config.yaml
   ```

2. **Build and run:**
   ```bash
   docker-compose up -d
   ```

## Prerequisites

Before running the Docker container, ensure you have:

1. **Docker** and **Docker Compose** installed
2. **Google Tasks API credentials** (`client_secret.json`)
3. **Notion Integration Token** and Database ID
4. **Configuration files** properly set up

## Configuration Setup

### Step 1: Configuration File

Create your `config.yaml` from the Docker template:

```bash
cp config.docker.yaml config.yaml
```

Edit `config.yaml` and update these values:
- `notion.token`: Your Notion integration token
- `notion.database_id`: Your Notion database ID  
- `default_list.id`: Your Google Tasks list ID
- Other settings as needed

### Step 2: Google Credentials

Download `client_secret.json` from Google Cloud Console and place it in the project root.

### Step 3: Token File

The `token.pkl` file will be created automatically on first run.

## Running the Container

### Option 1: Docker Compose (Recommended)

```bash
# Start the service (runs every 10 minutes)
docker-compose up -d

# View logs
docker-compose logs -f gtasks-notion-sync

# Stop the service  
docker-compose down
```

### Option 2: Manual Docker Run

```bash
docker run -d \
  --name gtasks-notion-sync \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/client_secret.json:/app/client_secret.json:ro \
  -v $(pwd)/token.pkl:/app/token.pkl \
  -v $(pwd)/logs:/app/logs \
  -e TZ=Asia/Kolkata \
  -e DOCKER_ENV=1 \
  gtasks-notion-integration:test
```

### Option 3: One-time Sync

Run sync once and exit:
```bash
docker run --rm -it \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/client_secret.json:/app/client_secret.json:ro \
  -v $(pwd)/token.pkl:/app/token.pkl \
  gtasks-notion-integration:test \
  python main.py --verbose
```

## Configuration Details

### Required Volume Mounts

| Host Path | Container Path | Purpose | Mode |
|-----------|----------------|---------|------|
| `./config.yaml` | `/app/config.yaml` | Main configuration | Read-only |
| `./client_secret.json` | `/app/client_secret.json` | Google credentials | Read-only |
| `./token.pkl` | `/app/token.pkl` | OAuth token storage | Read-write |
| `./logs` | `/app/logs` | Application logs | Read-write |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_ENV` | Enables Docker mode | `1` |
| `TZ` | Container timezone | `Asia/Kolkata` |
| `PYTHONUNBUFFERED` | Python output mode | `1` |

## Monitoring and Logs

### Health Monitoring

Check container health:
```bash
# Overall status
docker-compose ps

# Detailed health
docker inspect --format='{{.State.Health.Status}}' gtasks-notion-sync
```

### Log Access

```bash
# Real-time logs
docker-compose logs -f gtasks-notion-sync

# Log files (persistent)
tail -f logs/sync-$(date +%Y%m%d).log
```

## Security Features

- **No secrets in image**: All sensitive data mounted as volumes
- **Non-root user**: Container runs as `gtasks` user
- **Read-only mounts**: Configuration files mounted read-only
- **Resource limits**: Memory and CPU limits applied

## Troubleshooting

### Startup Validation

The container automatically validates:
- ✅ Configuration file exists and is valid YAML
- ✅ Google credentials file exists  
- ✅ Python environment is working
- ✅ Required dependencies installed

### Common Issues

**1. Config file not found:**
```bash
ERROR: config.yaml not found. Please mount it as a volume
```
**Solution:** Ensure `config.yaml` exists and is properly mounted.

**2. Invalid YAML format:**
```bash
ERROR: config.yaml is not valid YAML format
```
**Solution:** Check YAML syntax with `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`

**3. Google auth required:**
On first run, you may need to authenticate Google. Check logs for OAuth URL.

### Debug Mode

Run with verbose logging:
```bash
docker run --rm -it \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/client_secret.json:/app/client_secret.json:ro \
  -v $(pwd)/token.pkl:/app/token.pkl \
  gtasks-notion-integration:test \
  python main.py --verbose --dry-run
```

## Scheduling

The default container runs sync every 10 minutes. To customize:

1. **Change interval:** Edit `SYNC_INTERVAL` in `docker-entrypoint.sh`
2. **Use external scheduler:** Run one-time sync with cron/systemd
3. **Disable scheduling:** Override CMD to run once

## Resource Usage

Optimized for minimal resource usage:
- **Memory:** ~128MB typical, 256MB limit
- **CPU:** ~0.1 core typical, 0.5 core limit  
- **Storage:** ~100MB image size
- **Network:** Minimal HTTPS API calls only