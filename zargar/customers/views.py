"""
Placeholder views for customers module.
"""
from django.views.generic import TemplateView
from django.http import JsonResponse


class PlaceholderView(TemplateView):
    """
    Placeholder view for customers module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'customers',
            'status': 'placeholder',
            'message': 'Customers module will be implemented in later tasks'
        })