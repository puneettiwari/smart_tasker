# Task Workflow Generator API

Generate step-by-step workflows with validated Google searches using Claude AI.

## Features

- 🤖 AI-powered task breakdown using Claude Sonnet 4
- 🔍 Google search query generation
- ✅ Optional search validation
- 🎨 Beautiful web interface
- 🐳 Docker containerized
- 📊 FastAPI with automatic API docs

## Quick Start

### Local Development

1. **Clone and setup:**

```bash
git clone <your-repo>
cd task-workflow-generator
```

2. **Create `.env` file:**

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

3. **Run with Docker Compose:**

```bash
docker-compose up --build
```

4. **Access the app:**

- Web UI: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

### Without Docker

```bash
pip install -r requirements.txt
python -m app.main
```

## API Endpoints

### POST `/api/generate-workflow`

Generate a complete workflow with steps and searches.

**Request:**

```json
{
  "task": "Create an Excel chart with rounded bars",
  "validate_searches": false
}
```

**Response:**

```json
{
  "task": "Create an Excel chart with rounded bars",
  "task_summary": "Excel chart with rounded bar ends",
  "steps": [...],
  "total_steps": 4,
  "estimated_time": "10-15 minutes",
  "difficulty": "medium"
}
```

### POST `/api/quick-workflow`

Faster workflow generation without validation.

### GET `/health`

Health check endpoint.

## Deployment on AWS EC2

### 1. Launch EC2 Instance

```bash
# Amazon Linux 2 or Ubuntu 22.04
# Instance type: t2.micro or t2.small
# Security Group: Allow ports 22 (SSH) and 8001 (HTTP)
```

### 2. Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Docker
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker-compose --version
```

### 3. Deploy Application

```bash
# Clone your repository
git clone <your-repo>
cd task-workflow-generator

# Create .env file
nano .env
# Add: ANTHROPIC_API_KEY=your_key_here

# Start the application
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 4. Access Your App

```
http://your-ec2-public-ip:8001
```

### 5. Setup with Nginx (Optional - for production)

```bash
# Install Nginx
sudo yum install -y nginx

# Configure Nginx
sudo nano /etc/nginx/conf.d/task-workflow.conf
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Start Nginx
sudo service nginx start
# Update Security Group to allow port 80
```

### 6. Setup SSL with Let's Encrypt (Optional)

```bash
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Claude API key |
| `GOOGLE_API_KEY` | No | Google Custom Search API key |
| `GOOGLE_SEARCH_ENGINE_ID` | No | Google Custom Search Engine ID |
| `PORT` | No | API port (default: 8001) |

## Usage Examples

### Example 1: Excel Task

```
Task: "Create an Excel chart with rounded bars and gradient text"
```

### Example 2: PowerPoint Task

```
Task: "Create a PowerPoint presentation with stars on each slide in different colors"
```

### Example 3: Complex Task

```
Task: "Set up a Python virtual environment, install Flask, and create a basic API with authentication"
```

## Development

### Project Structure

```
task-workflow-generator/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── services/
│   │   ├── claude_service.py    # Claude API integration
│   │   └── search_service.py    # Google Search integration
│   └── static/
│       └── index.html       # Frontend UI
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Running Tests

```bash
# TODO: Add pytest tests
pytest
```

## Troubleshooting

### Container won't start

```bash
docker-compose logs
```

### API key not working

- Check .env file exists and has correct key
- Restart container: `docker-compose restart`

### Port already in use

```bash
# Change PORT in .env or docker-compose.yml
PORT=8001 docker-compose up
```

## Cost Estimate

**Claude API:**

- ~$0.03 per workflow (without validation)
- ~$0.10 per workflow (with validation)

**AWS EC2:**

- t2.micro: ~$8-10/month (Free tier eligible)
- t2.small: ~$17/month

## License

MIT

## Contributing

Pull requests welcome!

