import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from context import context
from config.config import ACTIVE_YEARS

class TestContext(unittest.TestCase):

    @patch('utils.seatable_manager.SeatableManager')
    @patch('context.context.sql_users')
    @patch('context.context.sql_urls')
    def test_table_user_aggregation(self, mock_sql_urls, mock_sql_users, mock_seatable_manager):
        # Setup mocks
        mock_client_2025 = MagicMock()
        mock_client_2026 = MagicMock()
        
        # Mock SeatableManager.get_seatable_instance to return different clients for different years
        def get_instance_side_effect(year):
            if year == 2025:
                return mock_client_2025
            elif year == 2026:
                return mock_client_2026
            return MagicMock()
            
        mock_seatable_manager.get_seatable_instance.side_effect = get_instance_side_effect
        
        # Mock sql_query returns
        mock_client_2025.sql_query.return_value = [{'name': 'User2025'}]
        mock_client_2026.sql_query.return_value = [{'name': 'User2026'}]
        
        # Clear cache before test
        context._table_user_for_year.cache_clear()
        
        # Execute
        result = context.table_user()
        
        # Verify
        self.assertEqual(len(result), 2)
        self.assertIn({'name': 'User2025'}, result)
        self.assertIn({'name': 'User2026'}, result)
        
        # Verify calls
        self.assertEqual(mock_seatable_manager.get_seatable_instance.call_count, 2)
        mock_client_2025.sql_query.assert_called()
        mock_client_2026.sql_query.assert_called()

    @patch('utils.seatable_manager.SeatableManager')
    @patch('context.context.sql_users')
    @patch('context.context.sql_urls')
    def test_get_urls_aggregation(self, mock_sql_urls, mock_sql_users, mock_seatable_manager):
        # Setup mocks
        mock_client_2025 = MagicMock()
        mock_client_2026 = MagicMock()
        
        def get_instance_side_effect(year):
            if year == 2025:
                return mock_client_2025
            elif year == 2026:
                return mock_client_2026
            return MagicMock()
            
        mock_seatable_manager.get_seatable_instance.side_effect = get_instance_side_effect
        
        mock_client_2025.sql_query.return_value = [{'url': 'http://2025.com'}]
        mock_client_2026.sql_query.return_value = [{'url': 'http://2026.com'}]
        
        # Clear cache
        context._get_urls_for_year.cache_clear()
        
        # Execute
        result = context.get_urls()
        
        # Verify
        self.assertEqual(len(result), 2)
        self.assertIn({'url': 'http://2025.com'}, result)
        self.assertIn({'url': 'http://2026.com'}, result)

if __name__ == '__main__':
    unittest.main()
