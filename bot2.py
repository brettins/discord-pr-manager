import os
import re
import json
from typing import Dict, Tuple, Optional, Any

import discord
from dotenv import load_dotenv

class PRBot(discord.Client):
    CONFIG_FILE = "bot_config.json"
    PR_PATTERN = re.compile(r'\[(.*?)\] Pull request (\w+): #(\d+) (.*)')
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        # Dictionary to store original notifications: key: (repository, pr_number), value: message
        self.pr_notifications: Dict[Tuple[str, str], discord.Message] = {}
        
        # Configuration storage - per guild settings
        self.guild_configs: Dict[int, Dict[str, Any]] = {}
        
        # Load existing configuration
        self.load_config()
    
    async def setup_hook(self) -> None:
        """Called when the client is done preparing the data received from Discord."""
        print(f"Bot is ready and logged in as {self.user}")
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    # JSON stores keys as strings, convert back to int for guild IDs
                    loaded_config = json.load(f)
                    self.guild_configs = {int(k): v for k, v in loaded_config.items()}
                    print(f"Loaded configuration for {len(self.guild_configs)} guilds")
        except Exception as e:
            print(f"Error loading configuration: {e}")
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.guild_configs, f)
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    async def on_ready(self) -> None:
        """Called when the client is done preparing the data received from Discord."""
        print(f'We have logged in as {self.user}')
        
        if self.guilds:
            for guild in self.guilds:
                print(f'Connected to guild: {guild.name} (ID: {guild.id})')
                if guild.id not in self.guild_configs:
                    self.guild_configs[guild.id] = {
                        "watch_channel": None,
                        "post_channel": None
                    }
                    self.save_config()
        else:
            print("No guilds found. The bot isn't in any server.")
    
    async def on_message(self, message: discord.Message) -> None:
        """Process incoming messages."""
        # Avoid processing messages sent by the bot itself
        if message.author == self.user:
            return
        
        # Get guild configuration
        guild_id = message.guild.id if message.guild else None
        config = self.guild_configs.get(guild_id, {}) if guild_id else {}
        
        # Check for admin commands
        if message.content.startswith('!prbot'):
            await self.handle_admin_commands(message, config, guild_id)
            return
        
        # Get the post and watch channels
        post_channel = self.get_post_channel(message, config)
        watch_channel_id = config.get("watch_channel")
        is_watch_channel = message.channel.id == watch_channel_id if watch_channel_id else False
        
        # Process GitHub messages with embeds
        if is_watch_channel and message.author.name == "GitHub" and message.embeds:
            await self.process_github_embeds(message, post_channel)
        
        # Simple parroting - if message is in watch channel, echo to post channel
        if is_watch_channel and message.channel.id != post_channel.id:
            await self.forward_message(message, post_channel)
        
        # Handle PR commands and notifications
        if message.content.startswith('!pr'):
            await self.handle_pr_command(message)
        elif self.PR_PATTERN.search(message.content):
            await self.process_pr_notification(message)
    
    async def handle_admin_commands(self, message: discord.Message, 
                                    config: Dict[str, Any], guild_id: int) -> None:
        """Handle administrative bot configuration commands."""
        # Check for admin permissions
        if not message.author.guild_permissions.administrator:
            await message.channel.send("You need administrator permissions to configure the bot.")
            return
        
        parts = message.content.split()
        if len(parts) < 2:
            await self.show_help(message)
            return
        
        command = parts[1].lower()
        
        if command == "watch":
            await self.set_watch_channel(message, parts, config, guild_id)
        elif command == "post":
            await self.set_post_channel(message, parts, config, guild_id)
        elif command == "status":
            await self.show_status(message, config)
    
    async def show_help(self, message: discord.Message) -> None:
        """Show help information for bot commands."""
        help_text = (
            "Available commands:\n"
            "!prbot watch <#channel> or !prbot watch channel_id - Set channel to watch for PR notifications\n"
            "!prbot post <#channel> or !prbot post channel_id - Set channel to post PR threads\n"
            "!prbot status - Show current configuration"
        )
        await message.channel.send(help_text)
    
    async def set_watch_channel(self, message: discord.Message, 
                               parts: list, config: Dict[str, Any], guild_id: int) -> None:
        """Set the channel to watch for PR notifications."""
        target_channel = self.get_target_channel(message, parts)
        
        if target_channel:
            config["watch_channel"] = target_channel.id
            self.guild_configs[guild_id] = config
            self.save_config()
            await message.channel.send(f"Watch channel set to {target_channel.mention}")
        else:
            await message.channel.send("Please specify a valid channel.")
    
    async def set_post_channel(self, message: discord.Message, 
                              parts: list, config: Dict[str, Any], guild_id: int) -> None:
        """Set the channel to post PR threads."""
        target_channel = self.get_target_channel(message, parts)
        
        if target_channel:
            config["post_channel"] = target_channel.id
            self.guild_configs[guild_id] = config
            self.save_config()
            await message.channel.send(f"Post channel set to {target_channel.mention}")
        else:
            await message.channel.send("Please specify a valid channel.")
    
    async def show_status(self, message: discord.Message, config: Dict[str, Any]) -> None:
        """Show current bot configuration status."""
        watch_channel = self.get_channel(config.get("watch_channel")) if config.get("watch_channel") else None
        post_channel = self.get_channel(config.get("post_channel")) if config.get("post_channel") else None
        
        status = "Current configuration:\n"
        status += f"Watch channel: {watch_channel.mention if watch_channel else 'Not set'}\n"
        status += f"Post channel: {post_channel.mention if post_channel else 'Not set'}"
        await message.channel.send(status)
    
    def get_target_channel(self, message: discord.Message, parts: list) -> Optional[discord.TextChannel]:
        """Parse and return a target channel from command parts."""
        # Check if a channel was mentioned using #channel format
        if message.channel_mentions:
            return message.channel_mentions[0]
        
        # If not, try to treat the third parameter as a channel ID
        if len(parts) >= 3:
            try:
                channel_id = int(parts[2])
                return self.get_channel(channel_id)
            except ValueError:
                return None
        
        return None
    
    def get_post_channel(self, message: discord.Message, config: Dict[str, Any]) -> discord.TextChannel:
        """Get the configured post channel or default to current channel."""
        post_channel = None
        if config.get("post_channel"):
            post_channel = self.get_channel(config["post_channel"])
        
        return post_channel or message.channel
    
    async def process_github_embeds(self, message: discord.Message, post_channel: discord.TextChannel) -> None:
        """Process GitHub message embeds to extract PR information."""
        for embed in message.embeds:
            # Check for PR related embeds
            if embed.title and "Pull request" in embed.title:
                match = self.PR_PATTERN.search(embed.title)
                if match:
                    repository, action, pr_number, description = self.parse_pr_match(match)
                    
                    # Create a unique key for this PR
                    key = (repository, pr_number)
                    
                    # Format a message for this PR
                    new_content = self.format_pr_message(repository, pr_number, description, action, embed)
                    
                    await self.update_or_create_pr_notification(key, new_content, post_channel, action)
    
    def parse_pr_match(self, match) -> Tuple[str, str, str, str]:
        """Parse PR information from regex match."""
        repository = match.group(1)    # e.g., "brettins/bot-test-repository"
        action = match.group(2)        # e.g., "opened", "closed"
        pr_number = match.group(3)     # e.g., "3"
        description = match.group(4)   # e.g., "Test PR for Discord Bot"
        return repository, action, pr_number, description
    
    def format_pr_message(self, repository: str, pr_number: str, 
                         description: str, action: str, embed: discord.Embed) -> str:
        """Format a message for a PR notification."""
        content = f"## [{repository}] PR #{pr_number}: {description}\n"
        content += f"**Status:** {action}\n"
        if embed.description:
            content += f"**Description:** {embed.description}\n"
        content += f"**Link:** {embed.url}"
        return content
    
    async def update_or_create_pr_notification(self, key: Tuple[str, str], 
                                              content: str, channel: discord.TextChannel, 
                                              action: str) -> None:
        """Update existing PR notification or create a new one."""
        if key in self.pr_notifications:
            # Update existing message
            try:
                original_message = self.pr_notifications[key]
                await original_message.edit(content=content)
                
                # Add status indicators based on action
                if action.lower() == "closed":
                    await original_message.add_reaction("✅")
                print(f"Updated PR message for {key[0]} #{key[1]}")
            except Exception as e:
                print(f"Failed to update PR message: {e}")
        else:
            # Create a new message for this PR
            try:
                pr_msg = await channel.send(content)
                self.pr_notifications[key] = pr_msg
                print(f"Created new PR message for {key[0]} #{key[1]}")
            except Exception as e:
                print(f"Failed to create PR message: {e}")
    
    async def forward_message(self, message: discord.Message, post_channel: discord.TextChannel) -> None:
        """Forward a message from watch channel to post channel."""
        content = f"**From {message.author.display_name} in {message.channel.name}:** {message.content}"
        
        # Also forward any attachments/embeds
        files = [await attachment.to_file() for attachment in message.attachments]
        
        await post_channel.send(content, files=files if files else None)
        print(f"Forwarded message from {message.channel.name} to {post_channel.name}")
    
    async def handle_pr_command(self, message: discord.Message) -> None:
        """Handle manual PR thread creation command (!pr)."""
        # Extract the content after the command
        pr_content = message.content[3:].strip()
        
        # Check if the content matches PR notification format
        match = self.PR_PATTERN.search(pr_content)
        if match:
            repository, action, pr_number, description = self.parse_pr_match(match)
            
            key = (repository, pr_number)
            new_content = f'[{repository}] Pull request {action}: #{pr_number} {description}'
            
            if key in self.pr_notifications:
                # PR already tracked, update the existing message
                await self.update_pr_notification(key, new_content, action, message)
            else:
                # New PR, create a message and store it
                bot_message = await message.channel.send(new_content)
                self.pr_notifications[key] = bot_message
        else:
            # Content doesn't match PR format, just echo it
            await message.channel.send(f"Creating PR thread: {pr_content}")
    
    async def update_pr_notification(self, key: Tuple[str, str], 
                                    content: str, action: str, 
                                    message: discord.Message) -> None:
        """Update an existing PR notification."""
        original_message = self.pr_notifications[key]
        try:
            await original_message.edit(content=content)
            
            # If this is a "closed" action, add a visual indicator
            if action.lower() == "closed":
                await original_message.add_reaction("✅")
            
            # Acknowledge the update
            await message.add_reaction("👍")
        except Exception as e:
            print(f"Failed to update message: {e}")
            # If update fails, create a new message
            await message.channel.send(f"Error updating PR status: {e}")
    
    async def process_pr_notification(self, message: discord.Message) -> None:
        """Process normal PR notifications (not from !pr command)."""
        match = self.PR_PATTERN.search(message.content)
        repository, action, pr_number, description = self.parse_pr_match(match)

        key = (repository, pr_number)
        
        if key in self.pr_notifications:
            # Update existing PR notification
            original_message = self.pr_notifications[key]
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
            self.pr_notifications[key] = message


# Main execution
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Retrieve the token from the environment variables
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    # Initialize and run the bot
    bot = PRBot()
    bot.run(TOKEN)

