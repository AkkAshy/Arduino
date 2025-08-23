from django.urls import path
from .views import (
    AlertMonitorListView,
    AlertStatsView,
    BulkAcknowledgeAlertsView,
    AlertDetailView,
    ActiveDevicesView
)

app_name = 'alert_monitor'

urlpatterns = [
    # Основные эндпоинты мониторинга
    path('alerts/', AlertMonitorListView.as_view(), name='alerts_list'),
    path('alerts/<int:alert_id>/', AlertDetailView.as_view(), name='alert_detail'),
    path('alerts/acknowledge/', BulkAcknowledgeAlertsView.as_view(), name='bulk_acknowledge'),
    
    # Статистика и аналитика
    path('stats/', AlertStatsView.as_view(), name='alert_stats'),
    path('devices/', ActiveDevicesView.as_view(), name='active_devices'),
]