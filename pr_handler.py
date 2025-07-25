import re
from typing import Dict, Tuple, Any
import datetime

import discord

from utils import get_status_color, get_status_icon

class PRHandler:
    """Handles processing and management of pull request notifications."""
    
    PR_PATTERN = re.compile(r'\[(.*?)\] Pull request (\w+): #(\d+) (.*)')
    
    def __init__(self):
        """Initialize the PR handler with empty notification dictionaries."""
        # Dictionary to store original notifications: key: (repository, pr_number), value: message
        self.pr_notifications: Dict[Tuple[str, str], discord.Message] = {}
        # Dictionary to store PR threads: key: (repository, pr_number), value: thread
        self.pr_threads: Dict[Tuple[str, str], discord.Thread] = {}
    
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
            
            # Create PR embed with icon
            status_icon = get_status_icon(action)
            embed = discord.Embed(
                title=f"{status_icon} PR #{pr_number}: {description}",
                description=f"Manual PR notification via command",
                color=get_status_color(action),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(name="Repository", value=repository, inline=True)
            embed.add_field(name="Status", value=f"{status_icon} {action.capitalize()}", inline=True)
            embed.add_field(name="Bot", value="🚧 LOCAL DEBUG", inline=True)
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
                
                # Create a thread for this PR
                thread_name = f"PR #{pr_number}: {description[:80]}..."  # Truncate if too long  
                try:
                    thread = await bot_message.create_thread(name=thread_name)
                    self.pr_threads[key] = thread
                    
                    # Send initial message to thread
                    await thread.send(f"🧵 **Thread created for PR #{pr_number}**\nUpdates and comments will appear here.")
                    
                except Exception as e:
                    print(f"❌ THREAD CREATION FAILED: {e}")
                    print(f"❌ Exception type: {type(e)}")
                    import traceback
                    print(f"❌ Full traceback: {traceback.format_exc()}")
                
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
    
    async def post_thread_update(self, key: Tuple[str, str], update_message: str) -> None:
        """Post an update to the PR thread."""
        if key in self.pr_threads:
            try:
                thread = self.pr_threads[key]
                await thread.send(update_message)
            except Exception as e:
                print(f"Failed to post thread update: {e}")
        else:
            print(f"No thread found for PR {key}")
    
    async def create_or_update_pr(self, repository: str, pr_number: str, action: str, 
                                 title: str, url: str = None, author: str = None, 
                                 channel: discord.TextChannel = None) -> discord.Message:
        """Create a new PR notification or update an existing one."""
        key = (repository, pr_number)
        status_icon = get_status_icon(action)
        
        embed = discord.Embed(
            title=f"{status_icon} PR #{pr_number}: {title}",
            url=url,
            color=get_status_color(action),
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.add_field(name="Repository", value=repository, inline=True)
        embed.add_field(name="Status", value=f"{status_icon} {action.capitalize()}", inline=True)
        
        if author:
            embed.add_field(name="Author", value=author, inline=True)
        
        embed.set_thumbnail(url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
        embed.set_footer(text=f"PR #{pr_number} • {repository}", icon_url="https://github.githubassets.com/favicons/favicon.png")
        
        if key in self.pr_notifications:
            # Update existing notification
            original_message = self.pr_notifications[key]
            try:
                await original_message.edit(embed=embed)
                return original_message
            except Exception as e:
                print(f"Failed to update existing PR notification: {e}")
                return None
        else:
            # Create new notification
            if not channel:
                print("No channel provided for new PR notification")
                return None
                
            try:
                message = await channel.send(embed=embed)
                self.pr_notifications[key] = message
                
                # Create thread
                thread_name = f"PR #{pr_number}: {title[:80]}..." if len(title) > 80 else f"PR #{pr_number}: {title}"
                print(f"DEBUG: Attempting to create thread '{thread_name}' for message {message.id}")
                print(f"DEBUG: Channel type: {channel.type}")
                print(f"DEBUG: Bot permissions in channel: {channel.permissions_for(channel.guild.me)}")
                
                thread = await message.create_thread(name=thread_name)
                self.pr_threads[key] = thread
                print(f"DEBUG: Thread created successfully! Thread ID: {thread.id}")
                
                # Send initial thread message
                await thread.send(f"🧵 **Thread created for PR #{pr_number}**\nUpdates and comments will appear here.")
                print(f"DEBUG: Initial message sent to thread")
                
                return message
            except Exception as e:
                print(f"Failed to create new PR notification: {e}")
                return None
