"""
API views for authentication and user management.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django.utils.translation import gettext_lazy as _

from .models import User
from .serializers import (
    TenantAwareTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    RoleUpdateSerializer,
    UserPermissionsSerializer,
    LoginSerializer
)
from .permissions import (
    TenantPermission,
    OwnerPermission,
    UserManagementPermission,
    SelfOrOwnerPermission,
    SuperAdminPermission
)
from .authentication import TenantAwareJWTAuthentication, SuperAdminAuthentication


class TenantAwareTokenObtainPairView(TokenObtainPairView):
    """
    JWT token obtain view with tenant awareness.
    """
    serializer_class = TenantAwareTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        """
        Obtain JWT tokens with tenant context.
        """
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(
                {'error': _('Authentication failed'), 'details': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LoginAPIView(APIView):
    """
    API view for user login with session and JWT support.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """
        Login user and return session + JWT tokens.
        """
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            remember_me = serializer.validated_data.get('remember_me', False)
            
            # Login user (creates session)
            login(request, user)
            
            # Set session expiry based on remember_me
            if remember_me:
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
            else:
                request.session.set_expiry(0)  # Browser session
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Add custom claims
            refresh['username'] = user.username
            refresh['role'] = getattr(user, 'role', 'user')
            refresh['schema'] = connection.schema_name
            
            if connection.schema_name != get_public_schema_name():
                refresh['is_tenant_user'] = True
                refresh['tenant_schema'] = connection.schema_name
            else:
                refresh['is_superadmin'] = SuperAdminAuthentication.is_superadmin(user)
            
            return Response({
                'message': _('Login successful'),
                'user': UserSerializer(user).data,
                'permissions': UserPermissionsSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'session_id': request.session.session_key
            }, status=status.HTTP_200_OK)
        
        return Response(
            {'error': _('Invalid credentials'), 'details': serializer.errors},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutAPIView(APIView):
    """
    API view for user logout.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Logout user and invalidate session.
        """
        try:
            # Blacklist refresh token if provided
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Logout user (destroys session)
            logout(request)
            
            return Response(
                {'message': _('Logout successful')},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': _('Logout failed'), 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    API view for user profile management.
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    
    def get_object(self):
        """
        Return current user.
        """
        return self.request.user
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on request method.
        """
        if self.request.method == 'GET':
            return UserSerializer
        return UserUpdateSerializer


class UserListCreateAPIView(generics.ListCreateAPIView):
    """
    API view for listing and creating users (owner only).
    """
    permission_classes = [permissions.IsAuthenticated, TenantPermission, UserManagementPermission]
    
    def get_queryset(self):
        """
        Return users in current tenant.
        """
        return User.objects.all().order_by('username')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on request method.
        """
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer


class UserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for user detail management.
    """
    permission_classes = [permissions.IsAuthenticated, TenantPermission, SelfOrOwnerPermission]
    
    def get_queryset(self):
        """
        Return users in current tenant.
        """
        return User.objects.all()
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on request method.
        """
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete user (deactivate instead of delete).
        """
        instance = self.get_object()
        
        # Prevent self-deletion
        if instance.id == request.user.id:
            return Response(
                {'error': _('You cannot delete your own account.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Deactivate user instead of deleting
        instance.is_active = False
        instance.save()
        
        return Response(
            {'message': _('User deactivated successfully.')},
            status=status.HTTP_200_OK
        )


class PasswordChangeAPIView(APIView):
    """
    API view for changing user password.
    """
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    
    def post(self, request):
        """
        Change user password.
        """
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': _('Password changed successfully.')},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'error': _('Password change failed'), 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class RoleUpdateAPIView(generics.UpdateAPIView):
    """
    API view for updating user roles (owner only).
    """
    serializer_class = RoleUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, TenantPermission, OwnerPermission]
    
    def get_queryset(self):
        """
        Return users in current tenant.
        """
        return User.objects.all()


class UserPermissionsAPIView(APIView):
    """
    API view for checking user permissions.
    """
    permission_classes = [permissions.IsAuthenticated, TenantPermission]
    
    def get(self, request, user_id=None):
        """
        Get user permissions.
        """
        if user_id:
            # Check specific user permissions (owner only)
            if not request.user.can_manage_users():
                return Response(
                    {'error': _('Permission denied.')},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response(
                    {'error': _('User not found.')},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Check current user permissions
            user = request.user
        
        serializer = UserPermissionsSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserActivationAPIView(APIView):
    """
    API view for activating/deactivating users (owner only).
    """
    permission_classes = [permissions.IsAuthenticated, TenantPermission, OwnerPermission]
    
    def post(self, request, user_id):
        """
        Activate or deactivate user.
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': _('User not found.')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prevent self-deactivation
        if user.id == request.user.id:
            return Response(
                {'error': _('You cannot deactivate your own account.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        action = request.data.get('action')
        if action == 'activate':
            user.is_active = True
            message = _('User activated successfully.')
        elif action == 'deactivate':
            user.is_active = False
            message = _('User deactivated successfully.')
        else:
            return Response(
                {'error': _('Invalid action. Use "activate" or "deactivate".')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.save()
        
        return Response(
            {'message': message, 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, TenantPermission])
def current_user_api(request):
    """
    API endpoint to get current user information.
    """
    serializer = UserSerializer(request.user)
    permissions_serializer = UserPermissionsSerializer(request.user)
    
    return Response({
        'user': serializer.data,
        'permissions': permissions_serializer.data,
        'schema': connection.schema_name,
        'is_superadmin': SuperAdminAuthentication.is_superadmin(request.user)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, TenantPermission])
def user_roles_api(request):
    """
    API endpoint to get available user roles.
    """
    roles = [
        {'value': 'owner', 'label': _('Owner'), 'description': _('Full access to all features')},
        {'value': 'accountant', 'label': _('Accountant'), 'description': _('Access to accounting and reporting')},
        {'value': 'salesperson', 'label': _('Salesperson'), 'description': _('Access to POS and customer management')},
    ]
    
    return Response({'roles': roles}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, TenantPermission])
def validate_token_api(request):
    """
    API endpoint to validate JWT token.
    """
    return Response({
        'valid': True,
        'user': UserSerializer(request.user).data,
        'schema': connection.schema_name
    }, status=status.HTTP_200_OK)