"""
Serializers for core authentication and user management.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import connection
from django_tenants.utils import get_public_schema_name

from .models import User


class TenantAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that handles tenant-aware authentication.
    """
    
    def validate(self, attrs):
        """
        Validate credentials and return JWT tokens with tenant context.
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError(
                _('Username and password are required.')
            )
        
        # Get current schema context
        current_schema = connection.schema_name
        
        # Authenticate user in current schema context
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError(
                _('Invalid credentials.')
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                _('User account is disabled.')
            )
        
        # Generate tokens
        refresh = self.get_token(user)
        
        # Add custom claims to token
        refresh['user_id'] = user.id
        refresh['username'] = user.username
        refresh['role'] = getattr(user, 'role', 'user')
        refresh['schema'] = current_schema
        
        # Add tenant-specific claims for regular users
        if current_schema != get_public_schema_name():
            refresh['is_tenant_user'] = True
            refresh['tenant_schema'] = current_schema
        else:
            refresh['is_superadmin'] = getattr(user, 'is_superuser', False)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
    
    @classmethod
    def get_token(cls, user):
        """
        Get token with custom claims.
        """
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['role'] = getattr(user, 'role', 'user')
        
        # Add Persian name if available
        if hasattr(user, 'full_persian_name'):
            token['persian_name'] = user.full_persian_name
        
        return token


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with role-based field access.
    """
    full_persian_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'persian_first_name', 'persian_last_name', 'full_persian_name',
            'phone_number', 'role', 'is_2fa_enabled', 'theme_preference',
            'is_active', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def to_representation(self, instance):
        """
        Customize representation based on user role and permissions.
        """
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        if request and request.user:
            # Only owners can see all user details
            if not request.user.can_manage_users():
                # Remove sensitive fields for non-owners
                sensitive_fields = ['email', 'phone_number']
                for field in sensitive_fields:
                    if field in data and request.user.id != instance.id:
                        data.pop(field, None)
        
        return data


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users (owner only).
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'persian_first_name', 'persian_last_name',
            'phone_number', 'role'
        ]
    
    def validate(self, attrs):
        """
        Validate password confirmation and role permissions.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {'password_confirm': _('Password confirmation does not match.')}
            )
        
        # Check if current user can create users with this role
        request = self.context.get('request')
        if request and request.user:
            if not request.user.can_manage_users():
                raise serializers.ValidationError(
                    _('You do not have permission to create users.')
                )
            
            # Only owners can create other owners
            if attrs.get('role') == 'owner' and not request.user.is_tenant_owner:
                raise serializers.ValidationError(
                    {'role': _('Only owners can create other owners.')}
                )
        
        return attrs
    
    def create(self, validated_data):
        """
        Create user with proper password hashing.
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user information.
    """
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'persian_first_name', 'persian_last_name',
            'phone_number', 'theme_preference', 'is_2fa_enabled'
        ]
    
    def update(self, instance, validated_data):
        """
        Update user with permission checks.
        """
        request = self.context.get('request')
        
        # Users can only update their own profile unless they're owners
        if request and request.user:
            if request.user.id != instance.id and not request.user.can_manage_users():
                raise serializers.ValidationError(
                    _('You can only update your own profile.')
                )
        
        return super().update(instance, validated_data)


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """
        Validate old password and new password confirmation.
        """
        user = self.context['request'].user
        
        # Check old password
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError(
                {'old_password': _('Current password is incorrect.')}
            )
        
        # Check new password confirmation
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {'new_password_confirm': _('New password confirmation does not match.')}
            )
        
        return attrs
    
    def save(self):
        """
        Save new password.
        """
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class RoleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user roles (owner only).
    """
    
    class Meta:
        model = User
        fields = ['role']
    
    def validate_role(self, value):
        """
        Validate role change permissions.
        """
        request = self.context.get('request')
        instance = self.instance
        
        if request and request.user:
            # Only owners can change roles
            if not request.user.can_manage_users():
                raise serializers.ValidationError(
                    _('You do not have permission to change user roles.')
                )
            
            # Cannot change own role
            if request.user.id == instance.id:
                raise serializers.ValidationError(
                    _('You cannot change your own role.')
                )
            
            # Only owners can promote to owner
            if value == 'owner' and not request.user.is_tenant_owner:
                raise serializers.ValidationError(
                    _('Only owners can promote users to owner role.')
                )
        
        return value


class UserPermissionsSerializer(serializers.Serializer):
    """
    Serializer for checking user permissions.
    """
    can_access_accounting = serializers.SerializerMethodField()
    can_access_pos = serializers.SerializerMethodField()
    can_manage_users = serializers.SerializerMethodField()
    is_tenant_owner = serializers.SerializerMethodField()
    
    def get_can_access_accounting(self, obj):
        return obj.can_access_accounting()
    
    def get_can_access_pos(self, obj):
        return obj.can_access_pos()
    
    def get_can_manage_users(self, obj):
        return obj.can_manage_users()
    
    def get_is_tenant_owner(self, obj):
        return obj.is_tenant_owner


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login form validation.
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={'input_type': 'password'})
    remember_me = serializers.BooleanField(required=False, default=False)
    
    def validate(self, attrs):
        """
        Validate login credentials.
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError(
                _('Username and password are required.')
            )
        
        # Authenticate user
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if not user:
            raise serializers.ValidationError(
                _('Invalid username or password.')
            )
        
        if not user.is_active:
            raise serializers.ValidationError(
                _('This account has been disabled.')
            )
        
        attrs['user'] = user
        return attrs