"""Test for __main__.py module."""

import sys
from unittest.mock import patch


def test_main_module():
    """Test that __main__.py can be imported and calls cli."""
    # Mock the cli to prevent actual execution
    with patch('claude_container.cli.main.cli') as mock_cli:
        # Import should work without error
        import claude_container.__main__
        # CLI should not be called on import
        mock_cli.assert_not_called()