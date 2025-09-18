"""
Placeholder views for POS module.
"""
from django.views.generic import TemplateView
from django.http import JsonResponse


class PlaceholderView(TemplateView):
    """
    Placeholder view for POS module.
    """
    def get(self, request, *args, **kwargs):
        return JsonResponse({
            'module': 'pos',
            'status': 'placeholder',
            'message': 'POS module will be implemented in later tasks'
        })