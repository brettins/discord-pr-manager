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
    """Get appropriate color for different PR statuses using 3-tier system."""
    status = status.lower()
    
    # Before merge states (Green)
    if status in ["opened", "open", "reopened", "ready_for_review", "review_requested", "draft"]:
        return discord.Color.green()
    # Merged state (Purple)
    elif status == "merged":
        return discord.Color.purple()
    # Abandoned/closed states (Red) 
    elif status in ["closed", "deleted"]:
        return discord.Color.red()
    else:
        # Default fallback
        return discord.Color.green()

def get_status_icon(status: str) -> str:
    """Get appropriate emoji icon for different PR statuses."""
    status = status.lower()
    
    # Before merge states
    if status == "opened" or status == "open":
        return "🟢"  # Green circle for open
    elif status == "reopened":
        return "🔄"  # Refresh for reopened
    elif status == "ready_for_review":
        return "👀"  # Eyes for ready for review
    elif status == "review_requested":
        return "📋"  # Clipboard for review requested
    elif status == "draft":
        return "📝"  # Memo for draft
    # Merged state
    elif status == "merged":
        return "🟣"  # Purple circle for merged
    # Abandoned states  
    elif status == "closed":
        return "🔴"  # Red circle for closed
    elif status == "deleted":
        return "🗑️"  # Trash for deleted
    else:
        return "🟢"  # Default to green circle
