import os
import json
import datetime
import asyncio
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, abort
import discord
from discord.ext import commands

from github_events import (
    PULL_REQUEST, PING, 
    PULL_REQUEST_REVIEW, ISSUE_COMMENT, PULL_REQUEST_REVIEW_COMMENT
)

# Import pyngrok if available
try:
    from pyngrok import ngrok, conf
    NGROK_AVAILABLE = True
except ImportError:
    NGROK_AVAILABLE = False

app = Flask(__name__)

# Reference to the Discord bot
bot = None
public_url = None

def set_bot_instance(bot_instance):
    """Set the Discord bot instance to allow webhook server to interact with Discord."""
    global bot
    bot = bot_instance

@app.route('/webhook/<int:guild_id>/<int:channel_id>/<token>', methods=['POST'])
def github_webhook(guild_id: int, channel_id: int, token: str):
    """
    Handle incoming GitHub webhooks with guild and channel info embedded in URL.
    
    URL format: /webhook/{guild_id}/{channel_id}/{token}
    The token is a simple verification string but not used for complex validation.
    """
    # Print headers and request info for debugging
    print(f"Received webhook for guild {guild_id}, channel {channel_id}")
    
    # Check if this is a ping event
    event_type = request.headers.get('X-GitHub-Event')
    if event_type == PING:
        print("Received ping event")
        return jsonify({"message": "Ping received!"}), 200
    
    # Validate the minimal required headers exist
    if not event_type:
        return jsonify({"error": "Missing X-GitHub-Event header"}), 400
    
    # Verify guild exists in our config
    if not verify_guild_token(guild_id, token):
        print(f"Invalid token for guild {guild_id}")
        abort(403, "Invalid token")
    
    # Process the payload
    payload = request.json
    if not payload:
        return jsonify({"error": "Missing or invalid JSON payload"}), 400
    
    # Handle pull request events - create a background task
    if event_type == PULL_REQUEST:
        # Create a task to process the PR asynchronously
        asyncio.run_coroutine_threadsafe(process_pull_request(payload, guild_id, channel_id), bot.loop)
        return jsonify({"message": "Webhook received, processing in background"}), 200
    
    # Handle pull request review events (UNVERIFIED EVENT NAME)
    elif event_type == PULL_REQUEST_REVIEW:
        asyncio.run_coroutine_threadsafe(process_pr_review(payload, guild_id, channel_id), bot.loop)
        return jsonify({"message": "PR review webhook received, processing in background"}), 200
    
    # Handle issue comment events (includes PR comments) (UNVERIFIED EVENT NAME)
    elif event_type == ISSUE_COMMENT:
        asyncio.run_coroutine_threadsafe(process_pr_comment(payload, guild_id, channel_id), bot.loop)
        return jsonify({"message": "Comment webhook received, processing in background"}), 200
    
    # Handle pull request review comment events (UNVERIFIED EVENT NAME)
    elif event_type == PULL_REQUEST_REVIEW_COMMENT:
        asyncio.run_coroutine_threadsafe(process_pr_review_comment(payload, guild_id, channel_id), bot.loop)
        return jsonify({"message": "Review comment webhook received, processing in background"}), 200
    
    # Handle other events as needed
    return jsonify({"message": f"Event {event_type} received but not processed"}), 200

def verify_guild_token(guild_id: int, token: str) -> bool:
    """
    Verify that the token is valid for the given guild.
    This is a simple verification that the guild exists and the token matches.
    """
    # Make sure the bot is initialized
    if not bot or not hasattr(bot, 'config_manager'):
        return False
    
    # Check if the guild exists in our bot's configuration
    guild_config = bot.config_manager.get_guild_config(guild_id)
    if not guild_config:
        return False
    
    # Verify the token matches what we have stored
    stored_token = guild_config.get("webhook_token")
    if not stored_token:
        # No token configured yet, accept any token for now
        return True
        
    # Simple equality check - not cryptographically secure but sufficient
    return token == stored_token

async def process_pull_request(payload: Dict[str, Any], guild_id: int, channel_id: int):
    """
    Process a pull request event and send notification to the specified Discord channel.
    This is an async function that will be run in the bot's event loop.
    """
    if not bot:
        print("Error: Discord bot instance not set")
        return
    
    try:
        # Extract PR information
        action = payload.get('action', '')
        pr_data = payload.get('pull_request', {})
        pr_number = pr_data.get('number', '')
        pr_title = pr_data.get('title', '')
        pr_url = pr_data.get('html_url', '')
        pr_body = pr_data.get('body', '')
        
        # Get repository information
        repo_data = payload.get('repository', {})
        repo_name = repo_data.get('full_name', '')
        
        # Check if the PR was merged (closed + merged flag)
        is_merged = False
        if action == 'closed' and pr_data.get('merged', False):
            action = 'merged'
            is_merged = True
        
        # Try to get the guild and channel
        guild = bot.get_guild(guild_id)
        if not guild:
            print(f"Error: Guild {guild_id} not found")
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            print(f"Error: Channel {channel_id} not found in guild {guild.name}")
            return
        
        # Use PR handler to create or update the notification
        try:
            if hasattr(bot, 'pr_handler'):
                # Get author info
                author = None
                if 'user' in pr_data and 'login' in pr_data['user']:
                    author = pr_data['user']['login']
                
                # Use the PR handler's create_or_update method
                message = await bot.pr_handler.create_or_update_pr(
                    repository=repo_name,
                    pr_number=str(pr_number),
                    action=action,
                    title=pr_title,
                    url=pr_url,
                    author=author,
                    channel=channel
                )
                
                if message:
                    print(f"Successfully processed PR notification for {repo_name} #{pr_number} - {action}")
                    
                    # Post status update to thread if this is a status change
                    pr_key = (repo_name, str(pr_number))
                    status_update = f"**Status Update:** {action.capitalize()}"
                    if pr_body and len(pr_body.strip()) > 0:
                        status_update += f"\n\n*Description:* {truncate_text(pr_body, 200)}"
                    
                    await bot.pr_handler.post_thread_update(pr_key, status_update)
                else:
                    print(f"Failed to process PR notification for {repo_name} #{pr_number}")
            else:
                print("PR handler not available")
        except Exception as e:
            print(f"Error processing PR with handler: {e}")
    
    except Exception as e:
        print(f"Error processing webhook: {e}")

def get_pr_color(action: str, is_merged: bool) -> int:
    """Get the appropriate color for the PR status."""
    if is_merged:
        return discord.Color.purple().value
    
    action = action.lower()
    if action == 'opened' or action == 'open':
        return discord.Color.yellow().value
    elif action == 'closed':
        # Use red for closed PRs (changes weren't incorporated)
        return discord.Color.red().value
    elif action == 'reopened':
        return discord.Color.orange().value
    elif 'draft' in action:
        return discord.Color.light_grey().value
    else:
        return discord.Color.blurple().value

def truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max_length and add ellipsis if needed."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def run_webhook_server(host='0.0.0.0', port=5000):
    """Run the Flask server with optional ngrok tunnel."""
    global public_url
    
    # Setup ngrok if available
    if NGROK_AVAILABLE:
        try:
            # Configure ngrok with auth token if provided
            ngrok_token = os.getenv('NGROK_AUTH_TOKEN')
            if ngrok_token:
                print("* Configuring ngrok with your auth token")
                conf.get_default().auth_token = ngrok_token
                
                # Set region if specified
                ngrok_region = os.getenv('NGROK_REGION')
                if ngrok_region:
                    conf.get_default().region = ngrok_region
            
            # Open a ngrok tunnel to the Flask app
            tunnel_url = os.getenv('WEBHOOK_BASE_URL')
            if not tunnel_url or tunnel_url == 'https://your-ngrok-url-here.ngrok.io':
                # Only create a new tunnel if URL is not already specified
                public_url = ngrok.connect(port).public_url
                print(f"* ngrok tunnel established at {public_url}")
                print(f"* Use this URL as your WEBHOOK_BASE_URL or in GitHub webhook settings")
                
                # Update the environment variable for the bot to use
                os.environ['WEBHOOK_BASE_URL'] = public_url
            else:
                public_url = tunnel_url
                print(f"* Using pre-configured webhook URL: {public_url}")
        except Exception as e:
            print(f"Error setting up ngrok: {e}")
            print("* Continue with local server only. Webhooks from GitHub won't work without a public URL.")
    
    # Start the Flask server
    app.run(host=host, port=port, debug=False)

async def process_pr_review(payload: Dict[str, Any], guild_id: int, channel_id: int):
    """Process a pull request review event and post to thread."""
    if not bot or not hasattr(bot, 'pr_handler'):
        print("Error: Discord bot or PR handler not available")
        return
    
    try:
        # Extract review information
        action = payload.get('action', '')
        review_data = payload.get('review', {})
        pr_data = payload.get('pull_request', {})
        
        pr_number = str(pr_data.get('number', ''))
        repo_name = payload.get('repository', {}).get('full_name', '')
        
        reviewer = review_data.get('user', {}).get('login', 'Unknown')
        review_state = review_data.get('state', '').lower()
        review_body = review_data.get('body', '')
        
        pr_key = (repo_name, pr_number)
        
        # Create thread update message
        if review_state == 'approved':
            emoji = "✅"
            status = "approved"
        elif review_state == 'changes_requested':
            emoji = "❌"
            status = "requested changes"
        elif review_state == 'commented':
            emoji = "💬"
            status = "commented"
        else:
            emoji = "📝"
            status = review_state
        
        update_message = f"{emoji} **{reviewer}** {status} this PR"
        if review_body:
            update_message += f"\n\n*Review:* {truncate_text(review_body, 300)}"
        
        await bot.pr_handler.post_thread_update(pr_key, update_message)
        print(f"Posted review update for {repo_name} #{pr_number}")
        
    except Exception as e:
        print(f"Error processing PR review: {e}")

async def process_pr_comment(payload: Dict[str, Any], guild_id: int, channel_id: int):
    """Process a pull request comment event and post to thread."""
    if not bot or not hasattr(bot, 'pr_handler'):
        print("Error: Discord bot or PR handler not available")
        return
    
    try:
        # Check if this is a PR comment (issue comments on PRs)
        issue_data = payload.get('issue', {})
        if not issue_data.get('pull_request'):
            # This is not a PR comment, skip
            return
            
        comment_data = payload.get('comment', {})
        action = payload.get('action', '')
        
        pr_number = str(issue_data.get('number', ''))
        repo_name = payload.get('repository', {}).get('full_name', '')
        
        commenter = comment_data.get('user', {}).get('login', 'Unknown')
        comment_body = comment_data.get('body', '')
        
        pr_key = (repo_name, pr_number)
        
        if action == 'created':
            emoji = "💬"
            update_message = f"{emoji} **{commenter}** commented on this PR\n\n*Comment:* {truncate_text(comment_body, 400)}"
        elif action == 'edited':
            emoji = "✏️"
            update_message = f"{emoji} **{commenter}** edited their comment\n\n*Updated comment:* {truncate_text(comment_body, 400)}"
        else:
            return  # Don't process other comment actions
        
        await bot.pr_handler.post_thread_update(pr_key, update_message)
        print(f"Posted comment update for {repo_name} #{pr_number}")
        
    except Exception as e:
        print(f"Error processing PR comment: {e}")

async def process_pr_review_comment(payload: Dict[str, Any], guild_id: int, channel_id: int):
    """Process a pull request review comment event and post to thread."""
    if not bot or not hasattr(bot, 'pr_handler'):
        print("Error: Discord bot or PR handler not available")
        return
    
    try:
        comment_data = payload.get('comment', {})
        pr_data = payload.get('pull_request', {})
        action = payload.get('action', '')
        
        pr_number = str(pr_data.get('number', ''))
        repo_name = payload.get('repository', {}).get('full_name', '')
        
        commenter = comment_data.get('user', {}).get('login', 'Unknown')
        comment_body = comment_data.get('body', '')
        file_path = comment_data.get('path', '')
        
        pr_key = (repo_name, pr_number)
        
        if action == 'created':
            emoji = "🔍"
            update_message = f"{emoji} **{commenter}** commented on code"
            if file_path:
                update_message += f" in `{file_path}`"
            update_message += f"\n\n*Review comment:* {truncate_text(comment_body, 400)}"
        else:
            return  # Don't process other review comment actions
        
        await bot.pr_handler.post_thread_update(pr_key, update_message)
        print(f"Posted review comment update for {repo_name} #{pr_number}")
        
    except Exception as e:
        print(f"Error processing PR review comment: {e}")

def get_public_url():
    """Return the public URL for the webhook server."""
    return public_url or os.getenv('WEBHOOK_BASE_URL', 'https://your-bot-domain.com')
