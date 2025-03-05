import os
import threading
import discord
from dotenv import load_dotenv

from config_manager import ConfigManager
from pr_handler import PRHandler
from command_handler import CommandHandler
from webhook_server import set_bot_instance, run_webhook_server, get_public_url

class PRBot(discord.Client):
    """Discord bot for managing GitHub pull request notifications."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.pr_handler = PRHandler()
        self.command_handler = CommandHandler(self)
        
        # Load existing configuration
        self.config_manager.load_config()
        
        # Set this bot instance for the webhook server
        set_bot_instance(self)
    
    async def setup_hook(self) -> None:
        """Called when the client is done preparing the data received from Discord."""
        print(f"Bot is ready and logged in as {self.user}")
    
    async def on_ready(self) -> None:
        """Called when the client is done preparing the data received from Discord."""
        print(f'We have logged in as {self.user}')
        
        if self.guilds:
            for guild in self.guilds:
                print(f'Connected to guild: {guild.name} (ID: {guild.id})')
                if guild.id not in self.config_manager.guild_configs:
                    self.config_manager.guild_configs[guild.id] = {
                        "webhook_token": None
                    }
                    self.config_manager.save_config()
        else:
            print("No guilds found. The bot isn't in any server.")
    
    async def on_message(self, message: discord.Message) -> None:
        """Process incoming messages."""
        # Avoid processing messages sent by the bot itself
        if message.author == self.user:
            return
        
        # Get guild configuration
        guild_id = message.guild.id if message.guild else None
        config = self.config_manager.get_guild_config(guild_id)
        
        # Check for admin commands (includes webhook command now)
        if message.content.startswith('!prbot'):
            await self.command_handler.handle_admin_commands(message, config, guild_id)
            return
            
        # Handle PR commands
        if message.content.startswith('!pr'):
            await self.pr_handler.handle_pr_command(message)


# Main execution
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Retrieve the token from the environment variables
    TOKEN = os.getenv('DISCORD_TOKEN')
    WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '5000'))
    
    # Initialize the bot
    bot = PRBot()
    
    # Start the webhook server in a separate thread
    webhook_thread = threading.Thread(
        target=run_webhook_server, 
        kwargs={'host': WEBHOOK_HOST, 'port': WEBHOOK_PORT},
        daemon=True
    )
    webhook_thread.start()

    
    # Run the Discord bot
    bot.run(TOKEN)
