# Deploying Discord PR Manager Bot to Digital Ocean

This guide covers deploying the bot to a Digital Ocean droplet and setting up proper infrastructure for reliability.

## 1. Initial Server Setup

### Create a Digital Ocean Droplet
- Create a new Ubuntu 22.04 LTS droplet (Basic plan, $5/month is sufficient)
- Set up SSH keys during creation for secure access

### Basic Server Configuration

```bash
# Create bot user
sudo adduser prbot
sudo usermod -aG sudo prbot

# Switch to the bot user
su - prbot
```

```bash
# Clone repository
git clone https://github.com/yourusername/discord-pr-manager.git
cd discord-pr-manager

# Create virtual environment
apt install python3.11-venv
python3 -m venv bot-env
source bot-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cat > .env << EOL
DISCORD_TOKEN=your_discord_bot_token
WEBHOOK_BASE_URL=https://prbot.simpleconnections.ca
WEBHOOK_HOST=127.0.0.1
WEBHOOK_PORT=5000
EOL

# Secure the environment file
chmod 600 .env
```

### nginx config

```bash
# Create Nginx configuration
apt install nginx
sudo nano /etc/nginx/sites-available/prbot.simpleconnections.ca
```

```nginx
server {
    listen 80;
    server_name prbot.simpleconnections.ca;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/prbot.simpleconnections.ca /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
apt install certbot python3-certbot-nginx
sudo certbot --nginx -d prbot.simpleconnections.ca
```

### Systemd Service

```bash
# Create systemd service
sudo nano /etc/systemd/system/prbot.service
```

```ini
[Unit]
Description=Discord PR Manager Bot
After=network.target

[Service]
User=prbot
WorkingDirectory=/home/prbot/discord-pr-manager
Environment="PATH=/home/prbot/discord-pr-manager/bot-env/bin"
ExecStart=/home/prbot/discord-pr-manager/bot-env/bin/python /home/prbot/discord-pr-manager/bot.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=discord-bot
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl enable prbot
sudo systemctl start prbot
```

## Important Considerations

1. **Environment Variables**: Make sure your production `.env` file contains:

    - `DISCORD_TOKEN`: Your Discord bot token
    - `WEBHOOK_BASE_URL`: The public URL where your bot is hosted
    - `WEBHOOK_HOST`: The local host where the bot is running
    - `WEBHOOK_PORT`: The port where the bot is listening

2. **Webhook Configuration**: With this setup, your webhook URL format will be:
`https://prbot.simpleconnections.ca/webhook/{guild_id}/{channel_id}/{token}`

3. **Updating the Bot**: When you need to update your bot:
```bash
su - prbot
cd discord-pr-manager
git pull
source bot-env/bin/activate
pip install -r requirements.txt
sudo systemctl restart discord-bot
```