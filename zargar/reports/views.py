"""
Placeholder views for reports module.
"""
from django.views.generic import TemplateView
from django.http import JsonResponse


class PlaceholderView(TemplateView):
    """
    Placeholder view for reports module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'reports',
            'status': 'placeholder',
            'message': 'Reports module will be implemented in later tasks'
        })