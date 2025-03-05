from typing import Tuple, Match

def parse_pr_match(match: Match) -> Tuple[str, str, str, str]:
    """Parse PR information from regex match."""
    repository = match.group(1)    # e.g., "brettins/bot-test-repository"
    action = match.group(2)        # e.g., "opened", "closed"
    pr_number = match.group(3)     # e.g., "3"
    description = match.group(4)   # e.g., "Test PR for Discord Bot"
    return repository, action, pr_number, description
