import pytest

from webhook_server import clean_body_text, truncate_text

DIFF_BREAKDOWN_BODY = """<!-- pr-diff-breakdown:start -->
```diff
@@ Diff breakdown @@
User facing           +27   -5
Test suite           +185   -8
```
<!-- pr-diff-breakdown:end -->

Adds GraphQL API health tests to CI so we catch schema regressions early.

<!-- Describe your changes above -->

## Testing
Ran locally.
"""


@pytest.mark.parametrize("body,expected", [
    (DIFF_BREAKDOWN_BODY,
     "Adds GraphQL API health tests to CI so we catch schema regressions early.\n\n## Testing\nRan locally."),
    ("<!-- pr-diff-breakdown:start -->\nstuff\n<!-- pr-diff-breakdown:end -->", ""),
    ("<!-- foo-start -->x<!-- foo-end -->keep", "keep"),
    ("<!-- X:START -->y<!-- X:END -->z", "z"),
    ("<!-- a:start -->x<!-- b:end -->keep", "xkeep"),
    ("<!-- pr-diff-breakdown:start -->\nreal description here", "real description here"),
    ("a\n<!-- x:start -->\n<!-- inner -->\n<!-- x:end -->\nb", "a\n\nb"),
    ("<!-- a:start -->1<!-- a:end -->mid<!-- b:start -->2<!-- b:end -->", "mid"),
    ("Just a normal description.", "Just a normal description."),
    ("See [PR](http://x) for `code` and <b>html</b>.", "See [PR](http://x) for `code` and <b>html</b>."),
    ("", ""),
    (None, ""),
])
def test_clean_body_text(body, expected):
    assert clean_body_text(body) == expected


def test_truncate_text_adds_ellipsis():
    assert truncate_text("abcdefghij", 8) == "abcde..."
    assert truncate_text("abc", 8) == "abc"
    assert truncate_text(None, 8) == ""
