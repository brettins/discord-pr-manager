# This example requires the 'message_content' intent.
import os
import re

from dotenv import load_dotenv
import discord

intents = discord.Intents.default()
intents.message_content = True
#
# Load environment variables from .env file
load_dotenv()

# Retrieve the token from the environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client(intents=intents)

# Dictionary to store original notifications: key: (repository, pr_number), value: message
pr_notifications = {}

# Regex to match a pull request notification message.
# Adjust this regex based on your actual notification format.
pr_pattern = re.compile(r'\[(.*?)\]\s+Pull request (\w+):\s+#(\d+)\s+(.*)')

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    if client.guilds:
        for guild in client.guilds:
            print(f'Connected to guild: {guild.name} (ID: {guild.id})')
    else:
        print("No guilds found. The bot isn't in any server.")


@client.event
async def on_message(message):
    # Avoid processing messages sent by the bot itself.
    if message.author == client.user:
        return

    # Optional: Check if the message is in a specific channel by comparing channel IDs.
    # if message.channel.id != YOUR_TARGET_CHANNEL_ID:
    #     return

    match = pr_pattern.search(message.content)
    if match:
        repository = match.group(1)       # e.g., Story-City/web-client
        action = match.group(2)           # e.g., opened, closed
        pr_number = match.group(3)        # e.g., 410
        description = match.group(4)      # additional details if any

        key = (repository, pr_number)
        new_content = f'[{repository}] Pull request {action}: #{pr_number} {description}'

        if key in pr_notifications:
            original_message = pr_notifications[key]
            print("pr notifictoins?")
            try:
                # Edit the original message with the updated content.
                print("trye 1")
                await original_message.edit(content=new_content)
                # Optionally, delete the new duplicate message.
                print("trye 2")
                await message.delete()
            except discord.Forbidden:
                print("Bot lacks permission to edit or delete messages.")
            except discord.HTTPException as e:
                print(f"Failed to update message: {e}")
        else:
            # If this is a new PR notification, store it.
            pr_notifications[key] = message

client.run(TOKEN)

