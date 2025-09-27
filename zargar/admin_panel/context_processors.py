"""
Context processors for admin panel.
"""
from django.urls import resolve
from .navigation import navigation_builder, breadcrumb_builder


def admin_navigation(request):
    """Add navigation context to admin panel templates."""
    context = {}
    
    # Only add navigation context for admin panel views
    if request.resolver_match and request.resolver_match.app_name == 'admin_panel':
        # Get navigation items for current user
        if hasattr(request, 'user') and request.user.is_authenticated:
            context['navigation_items'] = navigation_builder.get_navigation_for_user(request.user)
        else:
            context['navigation_items'] = []
        
        # Get breadcrumbs for current page
        current_url_name = None
        if request.resolver_match:
            current_url_name = f"{request.resolver_match.app_name}:{request.resolver_match.url_name}"
        
        context['breadcrumbs'] = breadcrumb_builder.get_breadcrumbs(current_url_name) if current_url_name else []
        context['current_url_name'] = current_url_name
    
    return context


def admin_theme(request):
    """Add theme context to admin panel templates."""
    return {
        'admin_theme': {
            'dark_mode_enabled': True,
            'rtl_enabled': True,
            'persian_numbers': True,
        }
    }