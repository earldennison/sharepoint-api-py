import pytest
import os
import logging
from unittest.mock import patch, MagicMock
from sharepoint_api.logging import configure_logging, logger


class TestLogging:

    def test_logger_exists(self):
        """Test that the logger is created"""
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "sharepoint_api"

    def test_configure_logging_basic(self):
        """Test that configure_logging configures the logger correctly"""
        # The function doesn't return the logger
        with patch('sharepoint_api.logging.logger', MagicMock()) as mock_logger:
            configure_logging()
            # Verify logger level was set
            mock_logger.setLevel.assert_called_once_with(logging.INFO)

    def test_configure_logging_with_level(self):
        """Test configuring logging with a specific level"""
        with patch('sharepoint_api.logging.logger', MagicMock()) as mock_logger:
            # Call with DEBUG level
            configure_logging(logging.DEBUG)

            # Verify the logger level was set
            mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

    def test_configure_logging_with_file(self):
        """Test configuring logging with a file handler"""
        with patch('sharepoint_api.logging.logger', MagicMock()) as mock_logger, \
                patch('logging.FileHandler') as mock_file_handler, \
                patch('logging.Formatter') as mock_formatter, \
                patch('os.makedirs') as mock_makedirs:

            # Create a mock handler
            mock_handler = MagicMock()
            mock_file_handler.return_value = mock_handler

            # Test with log file
            configure_logging(log_file='/tmp/test.log')

            # Verify the file handler was created and added
            mock_file_handler.assert_called_once_with('/tmp/test.log')
            mock_formatter.assert_called()
            mock_handler.setFormatter.assert_called_once()
            mock_handler.setLevel.assert_called_once()
            # The function adds both a console handler and a file handler
            assert mock_logger.addHandler.call_count == 2
            mock_logger.addHandler.assert_any_call(mock_handler)
