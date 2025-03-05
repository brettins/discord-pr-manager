# This example requires the 'message_content' intent.
import os
import re
import json

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
pr_pattern = re.compile(r'\[(.*?)\] Pull request (\w+): #(\d+) (.*)')

# Configuration storage - per guild settings
guild_configs = {}

# File to store persistent settings
CONFIG_FILE = "bot_config.json"

# Load existing configuration if available
def load_config():
    global guild_configs
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                # JSON stores keys as strings, convert back to int for guild IDs
                loaded_config = json.load(f)
                guild_configs = {int(k): v for k, v in loaded_config.items()}
                print(f"Loaded configuration for {len(guild_configs)} guilds")
    except Exception as e:
        print(f"Error loading configuration: {e}")

# Save configuration to file
def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(guild_configs, f)
    except Exception as e:
        print(f"Error saving configuration: {e}")

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    load_config()
    
    if client.guilds:
        for guild in client.guilds:
            print(f'Connected to guild: {guild.name} (ID: {guild.id})')
            if guild.id not in guild_configs:
                guild_configs[guild.id] = {
                    "watch_channel": None,
                    "post_channel": None
                }
                save_config()
    else:
        print("No guilds found. The bot isn't in any server.")


@client.event
async def on_message(message):
    # Avoid processing messages sent by the bot itself.
    if message.author == client.user:
        return
        
    # Get guild configuration
    guild_id = message.guild.id if message.guild else None
    config = guild_configs.get(guild_id, {}) if guild_id else {}
    
    # Check for admin commands to configure the bot
    if message.content.startswith('!prbot'):
        # Check for admin permissions
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You need administrator permissions to configure the bot.")
            return
            
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("Available commands:\n"
                                    "!prbot watch <#channel> or !prbot watch channel_id - Set channel to watch for PR notifications\n"
                                    "!prbot post <#channel> or !prbot post channel_id - Set channel to post PR threads\n"
                                    "!prbot status - Show current configuration")
            return

        # Handle watch command            
        if parts[1] == "watch":
            target_channel = None
            
            # Check if a channel was mentioned using #channel format
            if message.channel_mentions:
                target_channel = message.channel_mentions[0]
            # If not, try to treat the third parameter as a channel ID
            elif len(parts) >= 3:
                try:
                    channel_id = int(parts[2])
                    target_channel = client.get_channel(channel_id)
                except ValueError:
                    await message.channel.send("Invalid channel ID. Please provide a valid channel ID or mention.")
                    return
            
            if target_channel:
                config["watch_channel"] = target_channel.id
                guild_configs[guild_id] = config
                save_config()
                await message.channel.send(f"Watch channel set to {target_channel.mention}")
            else:
                await message.channel.send("Please specify a valid channel.")
                
        # Handle post command           
        elif parts[1] == "post":
            target_channel = None
            
            # Check if a channel was mentioned using #channel format
            if message.channel_mentions:
                target_channel = message.channel_mentions[0]
            # If not, try to treat the third parameter as a channel ID
            elif len(parts) >= 3:
                try:
                    channel_id = int(parts[2])
                    target_channel = client.get_channel(channel_id)
                except ValueError:
                    await message.channel.send("Invalid channel ID. Please provide a valid channel ID or mention.")
                    return
            
            if target_channel:
                config["post_channel"] = target_channel.id
                guild_configs[guild_id] = config
                save_config()
                await message.channel.send(f"Post channel set to {target_channel.mention}")
            else:
                await message.channel.send("Please specify a valid channel.")
            
        elif parts[1] == "status":
            watch_channel = client.get_channel(config.get("watch_channel")) if config.get("watch_channel") else None
            post_channel = client.get_channel(config.get("post_channel")) if config.get("post_channel") else None
            
            status = "Current configuration:\n"
            status += f"Watch channel: {watch_channel.mention if watch_channel else 'Not set'}\n"
            status += f"Post channel: {post_channel.mention if post_channel else 'Not set'}"
            await message.channel.send(status)
        
        return

    # Get the post channel (where PR threads will be created)
    post_channel = None
    if config.get("post_channel"):
        post_channel = client.get_channel(config["post_channel"])
    
    if not post_channel:
        post_channel = message.channel  # Default to current channel if not configured
    
    # Check if this is the watch channel
    watch_channel_id = config.get("watch_channel")
    is_watch_channel = message.channel.id == watch_channel_id if watch_channel_id else False
    
    # Process GitHub messages with embeds
    if is_watch_channel and message.author.name == "GitHub" and message.embeds:
        for embed in message.embeds:
            # Check for PR related embeds
            if embed.title and "Pull request" in embed.title:
                match = pr_pattern.search(embed.title)
                if match:
                    repository = match.group(1)    # e.g., "brettins/bot-test-repository"
                    action = match.group(2)        # e.g., "opened", "closed"
                    pr_number = match.group(3)     # e.g., "3"
                    description = match.group(4)   # e.g., "Test PR for Discord Bot"
                    
                    # Create a unique key for this PR
                    key = (repository, pr_number)
                    
                    # Format a message for this PR
                    new_content = f"## [{repository}] PR #{pr_number}: {description}\n"
                    new_content += f"**Status:** {action}\n"
                    if embed.description:
                        new_content += f"**Description:** {embed.description}\n"
                    new_content += f"**Link:** {embed.url}"
                    
                    # Check if we've seen this PR before
                    if key in pr_notifications:
                        # Update existing message
                        try:
                            original_message = pr_notifications[key]
                            await original_message.edit(content=new_content)
                            
                            # Add status indicators based on action
                            if action.lower() == "closed":
                                await original_message.add_reaction("✅")
                            print(f"Updated PR message for {repository} #{pr_number}")
                        except Exception as e:
                            print(f"Failed to update PR message: {e}")
                    else:
                        # Create a new message for this PR
                        try:
                            pr_msg = await post_channel.send(new_content)
                            pr_notifications[key] = pr_msg
                            print(f"Created new PR message for {repository} #{pr_number}")
                        except Exception as e:
                            print(f"Failed to create PR message: {e}")

    # Simple parroting - if message is in watch channel, echo to post channel
    if is_watch_channel and message.channel.id != post_channel.id:  # Avoid loops if same channel
        # Forward the message to the post channel
        content = f"**From {message.author.display_name} in {message.channel.name}:** {message.content}"
        
        # Also forward any attachments/embeds
        files = [await attachment.to_file() for attachment in message.attachments]
        
        await post_channel.send(content, files=files if files else None)
        print(f"Parroted message from {message.channel.name} to {post_channel.name}")

    # Process PR notifications logic would go here
    # For now we're just parroting to verify channels are working

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

