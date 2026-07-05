"""One-off maintenance: reconcile orphaned PR notification cards/threads.

The webhook race (fixed in pr_handler) left duplicate "opened" cards for some
PRs, each with its own thread, that no close event ever reached. This logs in
with the bot token, scans a channel's history, and for the PR numbers you name
edits every matching card to the given state (closed/merged) and archives +
locks its thread.

Dry-run by default; pass --apply to actually mutate.

Usage:
    python cleanup_orphans.py <channel_id> <state> <pr,pr,...> [--apply] [--limit N]

Example:
    python cleanup_orphans.py 1299172042607689748 closed 135,272,296,297 --apply
"""

import os
import re
import sys
import asyncio

import discord
from dotenv import load_dotenv

from utils import get_status_color, get_status_icon

PR_FOOTER_RE = re.compile(r'PR #(\d+)')


def parse_args(argv):
    if len(argv) < 3:
        print(__doc__)
        sys.exit(1)
    channel_id = int(argv[0])
    state = argv[1].lower()
    if state not in ("closed", "merged"):
        print(f"state must be 'closed' or 'merged', got {state!r}")
        sys.exit(1)
    numbers = {n.strip().lstrip('#') for n in argv[2].split(',') if n.strip()}
    apply = '--apply' in argv
    limit = 1000
    if '--limit' in argv:
        limit = int(argv[argv.index('--limit') + 1])
    return channel_id, state, numbers, apply, limit


def rebuild_embed(embed: discord.Embed, pr_number: str, state: str) -> discord.Embed:
    """Return a copy of embed re-skinned to the target state."""
    icon = get_status_icon(state)
    new = embed.copy()
    new.color = get_status_color(state)

    # Swap the leading status emoji in the title, keep the rest.
    title = embed.title or f"PR #{pr_number}"
    marker = f"PR #{pr_number}"
    idx = title.find(marker)
    new.title = f"{icon} {title[idx:]}" if idx != -1 else f"{icon} {title}"

    # Rewrite the Status field in place; leave every other field untouched.
    new.clear_fields()
    for field in embed.fields:
        if field.name == "Status":
            new.add_field(name="Status", value=f"{icon} {state.capitalize()}", inline=field.inline)
        else:
            new.add_field(name=field.name, value=field.value, inline=field.inline)
    return new


async def run():
    channel_id, state, numbers, apply, limit = parse_args(sys.argv[1:])
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("DISCORD_TOKEN not set")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        mode = "APPLY" if apply else "DRY-RUN"
        print(f"[{mode}] logged in as {client.user}; scanning channel {channel_id} "
              f"(last {limit}) for PRs {sorted(numbers)} -> {state}")
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)

        found = {n: {"cards": 0, "threads": 0, "thread_fail": 0} for n in numbers}
        try:
            async for msg in channel.history(limit=limit):
                if msg.author.id != client.user.id or not msg.embeds:
                    continue
                embed = msg.embeds[0]
                haystack = f"{embed.footer.text or ''} {embed.title or ''}"
                m = PR_FOOTER_RE.search(haystack)
                if not m or m.group(1) not in numbers:
                    continue
                prn = m.group(1)
                found[prn]["cards"] += 1
                thread = msg.thread
                print(f"  match PR #{prn}  msg={msg.id}  thread={'yes' if thread else 'no'}")
                if not apply:
                    continue
                try:
                    await msg.edit(embed=rebuild_embed(embed, prn, state))
                except Exception as e:
                    print(f"    ! card edit failed: {e}")
                if thread:
                    try:
                        # An already-archived thread can't be edited until it's
                        # unarchived, so unarchive first, then lock + re-archive.
                        if thread.archived:
                            await thread.edit(archived=False)
                        await thread.edit(locked=True, archived=True)
                        found[prn]["threads"] += 1
                    except Exception as e:
                        found[prn]["thread_fail"] += 1
                        print(f"    ! thread archive/lock failed: {e}")
        finally:
            print("\nsummary:")
            for n in sorted(numbers):
                f = found[n]
                print(f"  PR #{n}: cards={f['cards']} threads_locked={f['threads']} "
                      f"thread_fail={f['thread_fail']}")
            await client.close()

    await client.start(token)


if __name__ == "__main__":
    asyncio.run(run())
