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

    # Handle manual PR thread creation command
    if message.content.startswith('!pr'):
        # Extract the content after the command
        pr_content = message.content[3:].strip()
        
        # Check if the content matches PR notification format
        match = pr_pattern.search(pr_content)
        if match:
            repository = match.group(1)
            action = match.group(2)
            pr_number = match.group(3)
            description = match.group(4)
            
            key = (repository, pr_number)
            new_content = f'[{repository}] Pull request {action}: #{pr_number} {description}'
            
            if key in pr_notifications:
                # PR already tracked, update the existing message
                original_message = pr_notifications[key]
                try:
                    await original_message.edit(content=new_content)
                    
                    # If this is a "closed" action, add a visual indicator
                    if action.lower() == "closed":
                        await original_message.add_reaction("✅")
                    
                    # Acknowledge the update
                    await message.add_reaction("👍")
                except Exception as e:
                    print(f"Failed to update message: {e}")
                    # If update fails, create a new message
                    await message.channel.send(f"Error updating PR status: {e}")
            else:
                # New PR, create a message and store it
                bot_message = await message.channel.send(new_content)
                pr_notifications[key] = bot_message
                
        else:
            # Content doesn't match PR format, just echo it
            await message.channel.send(f"Creating PR thread: {pr_content}")
            
    # Process normal PR notifications (not from !pr command)
    elif pr_pattern.search(message.content):
        match = pr_pattern.search(message.content)
        repository = match.group(1)
        action = match.group(2)
        pr_number = match.group(3)
        description = match.group(4)

        key = (repository, pr_number)
        
        if key in pr_notifications:
            # Update existing PR notification
            original_message = pr_notifications[key]
            try:
                await original_message.edit(content=message.content)
                
                if action.lower() == "closed":
                    await original_message.add_reaction("✅")
                
                # Delete duplicate notification
                await message.delete()
            except Exception as e:
                print(f"Failed to update message: {e}")
        else:
            # New PR notification, store it
            pr_notifications[key] = message

client.run(TOKEN)

