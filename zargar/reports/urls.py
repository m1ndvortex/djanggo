"""
URLs for comprehensive reporting engine.
"""
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main dashboard
    path('', views.ReportsDashboardView.as_view(), name='dashboard'),
    
    # Report generation
    path('generate/', views.ReportGenerationView.as_view(), name='generate'),
    path('generate/<int:template_id>/', views.ReportGenerationView.as_view(), name='generate_template'),
    
    # Report management
    path('list/', views.ReportListView.as_view(), name='list'),
    path('detail/<str:report_id>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('download/<str:report_id>/<str:format>/', views.ReportDownloadView.as_view(), name='download'),
    
    # Report schedules
    path('schedules/', views.ReportScheduleListView.as_view(), name='schedule_list'),
    path('schedules/create/', views.ReportScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<int:pk>/edit/', views.ReportScheduleUpdateView.as_view(), name='schedule_edit'),
    path('schedules/<int:pk>/delete/', views.ReportScheduleDeleteView.as_view(), name='schedule_delete'),
    
    # Report templates
    path('templates/', views.ReportTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.ReportTemplateCreateView.as_view(), name='template_create'),
    
    # AJAX endpoints
    path('ajax/status/<str:report_id>/', views.ReportStatusAjaxView.as_view(), name='ajax_status'),
    path('ajax/gold-price/', views.GoldPriceAjaxView.as_view(), name='ajax_gold_price'),
]