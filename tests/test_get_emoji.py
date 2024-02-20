import pytest
from pan_os_upgrade.main import get_emoji


@pytest.mark.parametrize(
    "action, expected_emoji",
    [
        ("success", "✅"),
        ("warning", "🟧"),
        ("error", "❌"),
        ("working", "🔧"),
        ("report", "📝"),
        ("search", "🔍"),
        ("save", "💾"),
        ("skipped", "🟨"),
        ("stop", "🛑"),
        ("start", "🚀"),
        (
            "unknown",
            "",
        ),  # Testing an unknown action to ensure it returns an empty string
    ],
)
def test_get_emoji(action, expected_emoji):
    """Test that get_emoji returns the correct emoji for given actions and an empty string for unknown actions."""
    emoji = get_emoji(action)
    assert (
        emoji == expected_emoji
    ), f"Expected {expected_emoji} for action '{action}', but got '{emoji}'"
