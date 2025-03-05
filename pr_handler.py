import re
from typing import Dict, Tuple, Any

import discord

from utils import parse_pr_match

class PRHandler:
    """Handles processing and management of pull request notifications."""
    
    PR_PATTERN = re.compile(r'\[(.*?)\] Pull request (\w+): #(\d+) (.*)')
    
    def __init__(self):
        """Initialize the PR handler with an empty notification dictionary."""
        # Dictionary to store original notifications: key: (repository, pr_number), value: message
        self.pr_notifications: Dict[Tuple[str, str], discord.Message] = {}
    
    async def process_github_embeds(self, message: discord.Message, post_channel: discord.TextChannel) -> None:
        """Process GitHub message embeds to extract PR information."""
        for embed in message.embeds:
            # Check for PR related embeds
            if embed.title and "Pull request" in embed.title:
                match = self.PR_PATTERN.search(embed.title)
                if match:
                    repository, action, pr_number, description = parse_pr_match(match)
                    
                    # Create a unique key for this PR
                    key = (repository, pr_number)
                    
                    # Format a message for this PR
                    new_content = self.format_pr_message(repository, pr_number, description, action, embed)
                    
                    await self.update_or_create_pr_notification(key, new_content, post_channel, action)
    
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
    
    async def handle_pr_command(self, message: discord.Message) -> None:
        """Handle manual PR thread creation command (!pr)."""
        # Extract the content after the command
        pr_content = message.content[3:].strip()
        
        # Check if the content matches PR notification format
        match = self.PR_PATTERN.search(pr_content)
        if match:
            repository, action, pr_number, description = parse_pr_match(match)
            
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
        repository, action, pr_number, description = parse_pr_match(match)

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
