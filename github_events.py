# GitHub Webhook Event Types
# Reference: https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads

# VERIFIED EVENT TYPES (from existing code):
PULL_REQUEST = 'pull_request'  # Currently implemented in webhook_server.py
PING = 'ping'  # Currently implemented in webhook_server.py

# UNVERIFIED EVENT TYPES (need to be confirmed against GitHub docs):
# These are the event names I used but need verification:
PULL_REQUEST_REVIEW = 'pull_request_review'  # UNVERIFIED - used for reviews/approvals
ISSUE_COMMENT = 'issue_comment'  # UNVERIFIED - used for PR comments  
PULL_REQUEST_REVIEW_COMMENT = 'pull_request_review_comment'  # UNVERIFIED - used for code review comments

# TODO: Verify these event names against official GitHub webhook documentation
# TODO: Add any additional events that might be useful for PR tracking
# TODO: Document the payload structure for each event type

# Event actions we handle for pull_request events:
PR_ACTIONS = {
    'opened': 'PR opened',
    'closed': 'PR closed (check merged flag)',
    'reopened': 'PR reopened',
    'ready_for_review': 'PR ready for review (draft -> ready)',
    'converted_to_draft': 'PR converted to draft',
    'synchronize': 'PR updated with new commits',
    'edited': 'PR title/body edited'
}

# UNVERIFIED - Review states we handle:
REVIEW_STATES = {
    'approved': 'Review approved',
    'changes_requested': 'Changes requested',
    'commented': 'Review comment without approval/rejection'
}

# UNVERIFIED - Comment actions we handle:
COMMENT_ACTIONS = {
    'created': 'Comment created',
    'edited': 'Comment edited',
    'deleted': 'Comment deleted'
}