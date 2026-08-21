import discord
import pytest

from utils import get_status_color, get_status_icon
from webhook_server import resolve_pr_state


@pytest.mark.parametrize("action,pr_data,expected", [
    ("opened", {"draft": True}, "draft"),
    ("opened", {"draft": False}, "opened"),
    ("opened", {}, "opened"),
    ("converted_to_draft", {"draft": True}, "draft"),
    ("ready_for_review", {"draft": False}, "ready_for_review"),
    ("synchronize", {"draft": True}, "draft"),
    ("labeled", {"draft": False}, "labeled"),
    ("closed", {"merged": True}, "merged"),
    ("closed", {"merged": False}, "closed"),
    ("closed", {"merged": False, "draft": True}, "closed"),
])
def test_resolve_pr_state(action, pr_data, expected):
    assert resolve_pr_state(action, pr_data) == expected


@pytest.mark.parametrize("state,expected", [
    ("draft", discord.Color.light_grey()),
    ("converted_to_draft", discord.Color.light_grey()),
    ("Draft", discord.Color.light_grey()),
    ("opened", discord.Color.green()),
    ("ready_for_review", discord.Color.green()),
    ("merged", discord.Color.purple()),
    ("closed", discord.Color.red()),
])
def test_get_status_color(state, expected):
    assert get_status_color(state) == expected


def test_draft_icon():
    assert get_status_icon("draft") == "🛠️"
    assert get_status_icon("converted_to_draft") == "🛠️"
