"""
Placeholder views for accounting module.
"""
from django.views.generic import TemplateView
from django.http import JsonResponse


class PlaceholderView(TemplateView):
    """
    Placeholder view for accounting module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'accounting',
            'status': 'placeholder',
            'message': 'Accounting module will be implemented in later tasks'
        })