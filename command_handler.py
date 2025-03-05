from typing import Dict, Optional, Any
import secrets
import uuid

import discord
from webhook_server import get_public_url

class CommandHandler:
    """Handles command processing for the bot."""
    
    def __init__(self, bot):
        """Initialize with a reference to the bot client."""
        self.bot = bot
    
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
        elif command == "webhook":
            await self.generate_webhook_url(message, config, guild_id)
    
    async def show_help(self, message: discord.Message) -> None:
        """Show help information for bot commands."""
        help_text = (
            "Available commands:\n"
            "!prbot watch <#channel> or !prbot watch channel_id - Set channel to watch for PR notifications\n"
            "!prbot post <#channel> or !prbot post channel_id - Set channel to post PR threads\n"
            "!prbot status - Show current configuration\n"
            "!prbot webhook - Generate a GitHub webhook URL for the current channel\n\n"
            "Other commands:\n"
            "!pr [content] - Create a manual PR notification"
        )
        await message.channel.send(help_text)
    
    async def set_watch_channel(self, message: discord.Message, 
                              parts: list, config: Dict[str, Any], guild_id: int) -> None:
        """Set the channel to watch for PR notifications."""
        target_channel = self.get_target_channel(message, parts)
        
        if target_channel:
            self.bot.config_manager.update_guild_config(guild_id, "watch_channel", target_channel.id)
            await message.channel.send(f"Watch channel set to {target_channel.mention}")
        else:
            await message.channel.send("Please specify a valid channel.")
    
    async def set_post_channel(self, message: discord.Message, 
                             parts: list, config: Dict[str, Any], guild_id: int) -> None:
        """Set the channel to post PR threads."""
        target_channel = self.get_target_channel(message, parts)
        
        if target_channel:
            self.bot.config_manager.update_guild_config(guild_id, "post_channel", target_channel.id)
            await message.channel.send(f"Post channel set to {target_channel.mention}")
        else:
            await message.channel.send("Please specify a valid channel.")
    
    async def show_status(self, message: discord.Message, config: Dict[str, Any]) -> None:
        """Show current bot configuration status."""
        watch_channel = self.bot.get_channel(config.get("watch_channel")) if config.get("watch_channel") else None
        post_channel = self.bot.get_channel(config.get("post_channel")) if config.get("post_channel") else None
        
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
                return self.bot.get_channel(channel_id)
            except ValueError:
                return None
        
        return None
    
    def get_post_channel(self, message: discord.Message, config: Dict[str, Any]) -> discord.TextChannel:
        """Get the configured post channel or default to current channel."""
        post_channel = None
        if config.get("post_channel"):
            post_channel = self.bot.get_channel(config["post_channel"])
        
        return post_channel or message.channel

    async def generate_webhook_url(self, message: discord.Message, config: Dict[str, Any], guild_id: int) -> None:
        """Generate a webhook URL for the current server and channel."""
        channel_id = message.channel.id
        
        if not guild_id:
            await message.channel.send("This command only works in servers.")
            return
            
        # Generate a simple token if one doesn't exist
        webhook_token = config.get("webhook_token")
        
        if not webhook_token:
            # Simple random string, not used for cryptographic purposes
            webhook_token = str(uuid.uuid4())[:8]  # Just use first 8 chars of a UUID
            self.bot.config_manager.update_guild_config(guild_id, "webhook_token", webhook_token)
            
        # Get the base URL from environment variable or ngrok
        base_url = get_public_url()
        
        if base_url.startswith('https://your-bot-domain.com'):
            await message.channel.send("⚠️ No public URL configured. Please set WEBHOOK_BASE_URL in .env or install pyngrok.")
            return
        
        # Generate the webhook URL
        webhook_url = f"{base_url}/webhook/{guild_id}/{channel_id}/{webhook_token}"
        
        # Send the URL to the channel or via DM
        try:
            instructions = (
                f"**GitHub Webhook URL for {message.guild.name} / #{message.channel.name}**\n\n"
                f"1. Go to your GitHub repository → Settings → Webhooks → Add webhook\n\n"
                f"2. Enter this Payload URL:\n"
                f"```\n{webhook_url}\n```\n\n"
                f"3. Set Content type to: `application/json`\n\n"
                f"4. For events, select 'Let me select individual events' and choose at least 'Pull requests'\n\n"
                f"5. Click 'Add webhook'\n\n"
                f"GitHub will send a test 'ping' event - the bot should respond with success."
            )
            
            # Send instructions via DM to keep the URL somewhat private
            await message.author.send(instructions)
            
            await message.channel.send(f"I've sent the webhook setup instructions to your DMs, {message.author.mention}! "
                                    f"Check your direct messages.")
        except discord.Forbidden:
            # Cannot send DMs to the user, send in channel instead
            await message.channel.send(f"{message.author.mention}, I couldn't send you a DM. Here's the webhook URL:\n{webhook_url}")
