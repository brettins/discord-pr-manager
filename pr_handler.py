import re
from typing import Dict, Tuple, Any
import datetime

import discord

from utils import parse_pr_match, get_status_color

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
                    
                    # Create an embed for this PR
                    pr_embed = self.create_pr_embed(repository, pr_number, description, action, embed)
                    
                    await self.update_or_create_pr_notification(key, pr_embed, post_channel, action)
    
    def create_pr_embed(self, repository: str, pr_number: str, 
                        description: str, action: str, original_embed: discord.Embed) -> discord.Embed:
        """Create a rich embed for a PR notification."""
        # Create the embed with color based on action
        color = get_status_color(action)
        embed = discord.Embed(
            title=f"PR #{pr_number}: {description}",
            url=original_embed.url if original_embed.url else "",
            description=original_embed.description if original_embed.description else "",
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add repository field
        embed.add_field(name="Repository", value=repository, inline=True)
        
        # Add status field
        embed.add_field(name="Status", value=action.capitalize(), inline=True)
        
        # Add author from original embed if available
        if original_embed.author:
            name = original_embed.author.name
            url = original_embed.author.url
            icon_url = original_embed.author.icon_url
            embed.set_author(name=name, url=url, icon_url=icon_url)
        
        # Set GitHub icon as thumbnail
        embed.set_thumbnail(url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png")
        
        # Set footer
        embed.set_footer(text=f"PR #{pr_number} • {repository}", icon_url="https://github.githubassets.com/favicons/favicon.png")
        
        return embed
    
    async def update_or_create_pr_notification(self, key: Tuple[str, str], 
                                              embed: discord.Embed, channel: discord.TextChannel, 
                                              action: str) -> None:
        """Update existing PR notification or create a new one."""
        if key in self.pr_notifications:
            # Update existing message
            try:
                original_message = self.pr_notifications[key]
                await original_message.edit(embed=embed)
                print(f"Updated PR embed for {key[0]} #{key[1]}")
            except Exception as e:
                print(f"Failed to update PR embed: {e}")
        else:
            # Create a new message for this PR
            try:
                pr_msg = await channel.send(embed=embed)
                self.pr_notifications[key] = pr_msg
                print(f"Created new PR embed for {key[0]} #{key[1]}")
            except Exception as e:
                print(f"Failed to create PR embed: {e}")
    
    async def handle_pr_command(self, message: discord.Message) -> None:
        """Handle manual PR thread creation command (!pr)."""
        # Extract the content after the command
        pr_content = message.content[3:].strip()
        
        # Check if the content matches PR notification format
        match = self.PR_PATTERN.search(pr_content)
        if match:
            repository, action, pr_number, description = parse_pr_match(match)
            
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
    
    async def process_pr_notification(self, message: discord.Message) -> None:
        """Process normal PR notifications (not from !pr command)."""
        match = self.PR_PATTERN.search(message.content)
        repository, action, pr_number, description = parse_pr_match(match)

        key = (repository, pr_number)
        
        # Create embed for this PR notification
        embed = discord.Embed(
            title=f"PR #{pr_number}: {description}",
            description="PR notification from text message",
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
            # Update existing PR notification
            original_message = self.pr_notifications[key]
            try:
                await original_message.edit(embed=embed)
                # Delete duplicate notification
                await message.delete()
            except Exception as e:
                print(f"Failed to update message: {e}")
        else:
            # New PR notification, create an embed message
            try:
                bot_message = await message.channel.send(embed=embed)
                self.pr_notifications[key] = bot_message
                # Delete original text message
                await message.delete()
            except Exception as e:
                print(f"Failed to process PR notification: {e}")
