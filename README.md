# Text-to-Speech Web Application

A web-based Text-to-Speech (TTS) application that converts text to natural-sounding speech. The application supports both English and Chinese text input, and provides immediate playback and MP3 download options.

Live demo: [http://text2speech.help/](http://text2speech.help/)

![Main Interface](https://github.com/EricZhou866/Text2Speech/blob/main/tts/static/tts-ui.png)


## Features

- 🌐 Multi-language Support
  - English & Chinese
  - Auto language detection
  - Mixed language support
  - Natural pronunciation

- 🎤 Voice Options
  - Male voices: US & Chinese
  - Female voices: US & Chinese
  - High-quality synthesis
  - Natural transitions

- ⚡ Performance
  - Fast processing
  - Handles long text
  - Concurrent processing
  - Memory efficient

- 🎯 Easy to Use
  - Clean interface
  - Auto playback
  - One-click download
  - Mobile friendly

## Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/text-to-speech.git

# Install dependencies
pip install -r requirements.txt

# Start application
python app.py
Visit http://localhost:5001 in your browser.
API Usage
Convert text to speech:
import requests

url = 'http://localhost:5001/tts'
data = {
    'text': 'Hello World! 你好世界！',
    'voice': 'male'  # or 'female'
}

response = requests.post(url, json=data)
if response.status_code == 200:
    with open('output.mp3', 'wb') as f:
        f.write(response.content)
License
MIT License - see LICENSE file for details.

```markdown
# Installation Guide

## Prerequisites

- Python 3.8+
- pip package manager
- nginx (for production)
- System memory: 2GB minimum
- Storage space: 1GB minimum

## Development Setup

1. Install Python dependencies:
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows

# Install packages
pip install quart quart-cors hypercorn edge-tts
2.	Configure application:
# Create temp directory
mkdir temp
chmod 755 temp

# Set environment variables (optional)
export MAX_CONCURRENT_TASKS=4
export DEFAULT_TIMEOUT=30
3.	Run development server:
python app.py
Production Deployment
1. System Preparation
# Update system
sudo apt update && sudo apt upgrade

# Install required packages
sudo apt install python3-pip nginx
2. Application Setup
# Create application directory
sudo mkdir -p /opt/tts
cd /opt/tts

# Clone repository
git clone https://github.com/EricZhou866/Text2Speech.git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
3. Configure Service
Create systemd service file:
sudo nano /etc/systemd/system/tts.service
Add content:
[Unit]
Description=Text to Speech Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tts
Environment="PATH=/opt/tts/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/tts/venv/bin/hypercorn app:app --bind 127.0.0.1:5001
Restart=always

[Install]
WantedBy=multi-user.target
4. Configure Nginx
Create nginx configuration:
sudo nano /etc/nginx/sites-available/tts
Add content:
server {
    listen 80;
    server_name your_domain.com;

    access_log /var/log/nginx/tts-access.log;
    error_log /var/log/nginx/tts-error.log;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
Enable site:
sudo ln -s /etc/nginx/sites-available/tts /etc/nginx/sites-enabled/
5. Set Permissions
# Set ownership
sudo chown -R www-data:www-data /opt/tts

# Set directory permissions
sudo chmod 755 /opt/tts
sudo chmod -R 755 /opt/tts/temp
6. Start Services
# Start and enable TTS service
sudo systemctl start tts
sudo systemctl enable tts

# Restart nginx
sudo systemctl restart nginx
7. Verify Installation
# Check service status
sudo systemctl status tts

# Check logs
sudo journalctl -u tts -f

# Test API
curl -X POST http://localhost:5001/tts \
     -H "Content-Type: application/json" \
     -d '{"text":"Test", "voice":"male"}' \
     --output test.mp3
Maintenance
Log Rotation
Create logrotate configuration:
sudo nano /etc/logrotate.d/tts
Add content:
Copy
/var/log/nginx/tts-*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ ! -f /var/run/nginx.pid ] || kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
Monitoring
Monitor service status:
# CPU and memory usage
top -p $(pgrep -f hypercorn)

# Disk usage
du -sh /opt/tts/temp/

# Service status
systemctl status tts
Troubleshooting
Common Issues
1.	Service won't start:
# Check logs
sudo journalctl -u tts -f

# Verify permissions
sudo chown -R www-data:www-data /opt/tts
sudo chmod 755 /opt/tts
2.	Nginx errors:
# Test configuration
sudo nginx -t

# Check logs
tail -f /var/log/nginx/error.log
3.	Permission issues:
# Reset permissions
sudo find /opt/tts -type d -exec chmod 755 {} \;
sudo find /opt/tts -type f -exec chmod 644 {} \;
Performance Tuning
1.	Adjust worker count in systemd service:
ExecStart=/opt/tts/venv/bin/hypercorn app:app --workers 4 --bind 127.0.0.1:5001
2.	Optimize nginx configuration:
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
client_max_body_size 10M;
3.	Configure system limits:
# /etc/security/limits.conf
www-data soft nofile 65535
www-data hard nofile 65535
Updates
To update the application:
cd /opt/tts
source venv/bin/activate
git pull
pip install -r requirements.txt
sudo systemctl restart tts
Support
For issues and support:
•	GitHub Issues: Create Issue
•	Email: EricZhou866@gmail.com



