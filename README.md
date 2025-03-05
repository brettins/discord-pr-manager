# Discord PR Manager Bot

A Discord bot that receives GitHub webhook notifications for Pull Requests and posts them to your Discord channels.

## Features

- Receive GitHub webhook events for pull requests
- Display rich PR notifications as embeds in Discord channels
- Update existing PR notifications when status changes (opened, closed, merged)
- Create manual PR notifications using the `!pr` command
- Automatic ngrok tunnel creation for webhook development

## Setup

### Requirements

- Python 3.8+
- Discord Bot Token
- GitHub repository with admin access (to set up webhooks)

### Installation

1. Clone this repository
```
git clone https://github.com/discord/discord-example-app.git
```

2. Navigate to its directory and install dependencies:
```
cd discord-example-app
pip install -r requirements.txt
```

3. Fetch the credentials from your app's settings and add them to a `.env` file. You'll need your bot token (`DISCORD_TOKEN`) and GitHub secret (`GITHUB_SECRET`).

4. Install slash commands:
```
python register_commands.py
```

5. Run the bot:
```
python bot.py
```

### Set up interactivity

The project needs a public endpoint where GitHub can send requests. To develop and test locally, you can use something like [`ngrok`](https://ngrok.com/) to tunnel HTTP traffic.

Install ngrok if you haven't already, then start listening on port `3000`:
```
ngrok http 3000
```

You should see your connection open:
```
Tunnel Status                 online
Version                       2.0/2.0
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://1234-someurl.ngrok.io -> localhost:3000

Connections                  ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

Copy the forwarding address that starts with `https`, in this case `https://1234-someurl.ngrok.io`, then go to your [GitHub repository settings](https://github.com/your-repo/settings/hooks).

Add a new webhook with the following settings:
- **Payload URL**: `https://1234-someurl.ngrok.io/webhook`
- **Content type**: `application/json`
- **Secret**: Your GitHub secret

Click **Add webhook**, and your bot should be ready to run 🚀

## Other resources
- Read **[the documentation](https://discord.com/developers/docs/intro)** for in-depth information about API features.
- Join the **[Discord Developers server](https://discord.gg/discord-developers)** to ask questions about the API, attend events hosted by the Discord API team, and interact with other devs.
- Check out **[community resources](https://discord.com/developers/docs/topics/community-resources#community-resources)** for language-specific tools maintained by community members.
