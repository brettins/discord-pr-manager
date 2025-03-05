from typing import Tuple, Match
import discord

def parse_pr_match(match: Match) -> Tuple[str, str, str, str]:
    """Parse PR information from regex match."""
    repository = match.group(1)    # e.g., "brettins/bot-test-repository"
    action = match.group(2)        # e.g., "opened", "closed"
    pr_number = match.group(3)     # e.g., "3"
    description = match.group(4)   # e.g., "Test PR for Discord Bot"
    return repository, action, pr_number, description

def get_status_color(status: str) -> discord.Color:
    """Get appropriate color for different PR statuses."""
    status = status.lower()
    
    if status == "opened" or status == "open":
        # Yellow for open PRs
        return discord.Color.yellow()
    elif status == "closed":
        # Red for closed PRs (changes weren't incorporated)
        return discord.Color.red()
    elif status == "merged":
        # Purple for merged PRs
        return discord.Color.purple()
    elif status == "reopened":
        # Orange for reopened PRs
        return discord.Color.orange() 
    elif "draft" in status:
        # Gray for draft PRs
        return discord.Color.light_grey()
    elif "review" in status:
        # Blue for PRs under review
        return discord.Color.blue()
    else:
        # Default color
        return discord.Color.blurple()
