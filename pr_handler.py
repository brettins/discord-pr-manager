import re
from typing import Dict, Tuple, Any
import datetime

import discord

from utils import get_status_color

class PRHandler:
    """Handles processing and management of pull request notifications."""
    
    PR_PATTERN = re.compile(r'\[(.*?)\] Pull request (\w+): #(\d+) (.*)')
    
    def __init__(self):
        """Initialize the PR handler with an empty notification dictionary."""
        # Dictionary to store original notifications: key: (repository, pr_number), value: message
        self.pr_notifications: Dict[Tuple[str, str], discord.Message] = {}
    
    async def handle_pr_command(self, message: discord.Message) -> None:
        """Handle manual PR thread creation command (!pr)."""
        # Extract the content after the command
        pr_content = message.content[3:].strip()
        
        # Check if the content matches PR notification format
        match = self.PR_PATTERN.search(pr_content)
        if match:
            repository = match.group(1)    # e.g., "brettins/bot-test-repository"
            action = match.group(2)        # e.g., "opened", "closed"
            pr_number = match.group(3)     # e.g., "3"
            description = match.group(4)   # e.g., "Test PR for Discord Bot"
            
            key = (repository, pr_number)
            
            # Create PR embed
            embed = discord.Embed(
                title=f"PR #{pr_number}: {description}",
                description=f"Manual PR notification via command",
                color=get_status_color(action),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(name="Repository", value=repository, inline=True)
            embed.add_field(name="Status", value=action.capitalize(), inline=True)
            embed.set_footer(text=f"PR #{pr_number} • {repository}", icon_url="https://github.githubassets.com/favicons/favicon.png")
            
            # Try to build a GitHub URL
            if '/' in repository:
                # Standard GitHub repo format: username/repository
                url = f"https://github.com/{repository}/pull/{pr_number}"
                embed.url = url
                
            if key in self.pr_notifications:
                # PR already tracked, update the existing message
                await self.update_pr_notification(key, embed, message)
            else:
                # New PR, create a message and store it
                bot_message = await message.channel.send(embed=embed)
                self.pr_notifications[key] = bot_message
                await message.add_reaction("✅")
        else:
            # Content doesn't match PR format, just echo it
            await message.channel.send(f"Creating PR thread: {pr_content}")
    
    async def update_pr_notification(self, key: Tuple[str, str], 
                                    embed: discord.Embed, 
                                    message: discord.Message) -> None:
        """Update an existing PR notification."""
        original_message = self.pr_notifications[key]
        try:
            await original_message.edit(embed=embed)
            # Acknowledge the update
            await message.add_reaction("👍")
        except Exception as e:
            print(f"Failed to update message: {e}")
            # If update fails, create a new message
            await message.channel.send(f"Error updating PR status: {e}")
