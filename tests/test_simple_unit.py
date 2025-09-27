"""
Simple unit test to verify testing infrastructure works.
"""
import pytest
from unittest.mock import Mock, patch


class TestSimpleUnit:
    """Simple unit tests that don't require database."""
    
    def test_basic_functionality(self):
        """Test basic Python functionality."""
        assert 1 + 1 == 2
        assert "hello" == "hello"
        assert [1, 2, 3] == [1, 2, 3]
    
    def test_mock_functionality(self):
        """Test mock functionality."""
        mock_obj = Mock()
        mock_obj.method.return_value = "test"
        
        result = mock_obj.method()
        assert result == "test"
        mock_obj.method.assert_called_once()
    
    def test_patch_functionality(self):
        """Test patch functionality."""
        with patch('builtins.len') as mock_len:
            mock_len.return_value = 5
            
            result = len([1, 2, 3])
            assert result == 5
            mock_len.assert_called_once_with([1, 2, 3])
    
    def test_imports_work(self):
        """Test that our imports work."""
        # Test Django imports
        try:
            import django
            from django.conf import settings
            django_available = True
        except ImportError:
            django_available = False
        
        assert django_available, "Django should be available"
        
        # Test our app imports
        try:
            from zargar.admin_panel.unified_auth_backend import UnifiedSuperAdminAuthBackend
            backend_available = True
        except ImportError:
            backend_available = False
        
        assert backend_available, "Our unified auth backend should be importable"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])