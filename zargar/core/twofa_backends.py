"""
Custom authentication backends for 2FA integration.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import TOTPDevice
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


# Legacy 2FA backends removed - 2FA is now handled by UnifiedSuperAdminAuthBackend