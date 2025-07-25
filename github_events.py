# GitHub Webhook Event Types
# Reference: https://docs.github.com/en/developers/webhooks-and-events/webhooks/webhook-events-and-payloads

# ✅ VERIFIED EVENT TYPES (from GitHub docs):
PULL_REQUEST = 'pull_request'  # PR opened, closed, merged, etc.
PING = 'ping'  # Webhook confirmation
PULL_REQUEST_REVIEW = 'pull_request_review'  # PR reviews (approved, changes_requested, etc.)
ISSUE_COMMENT = 'issue_comment'  # Comments on PRs and issues
PULL_REQUEST_REVIEW_COMMENT = 'pull_request_review_comment'  # Code review comments on PR diffs

# Additional GitHub events we might want to support in future:
# - 'push': When commits are pushed to branches
# - 'release': When releases are created
# - 'workflow_run': When GitHub Actions complete

# ✅ VERIFIED pull_request event actions (from GitHub docs):
PR_ACTIONS = {
    'opened': 'PR opened',
    'closed': 'PR closed (check merged flag to determine if merged or abandoned)',
    'reopened': 'PR reopened', 
    'ready_for_review': 'PR ready for review (draft -> ready)',
    'converted_to_draft': 'PR converted to draft',
    'synchronize': 'PR updated with new commits',
    'edited': 'PR title/body edited',
    'assigned': 'PR assigned to user',
    'review_requested': 'Review requested from user/team'
}

# ✅ VERIFIED pull_request_review states (from GitHub docs):
REVIEW_STATES = {
    'approved': 'Review approved',
    'changes_requested': 'Changes requested', 
    'commented': 'Review comment without approval/rejection',
    'dismissed': 'Review was dismissed'
}

# ✅ VERIFIED comment actions for issue_comment and pull_request_review_comment:
COMMENT_ACTIONS = {
    'created': 'Comment created',
    'edited': 'Comment edited', 
    'deleted': 'Comment deleted'
}