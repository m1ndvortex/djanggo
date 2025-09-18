"""
Placeholder views for jewelry module.
"""
from django.views.generic import TemplateView
from django.http import JsonResponse


class PlaceholderView(TemplateView):
    """
    Placeholder view for jewelry module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'jewelry',
            'status': 'placeholder',
            'message': 'Jewelry module will be implemented in later tasks'
        })