from django.urls import path
from .views import (
    SensorDataView, AlertListView, AcknowledgeAlertView,
    DeviceSettingsView, DeviceStatusView, BufferCleanupView, TestSensorView
)

app_name = 'sensors'

urlpatterns = [
    # Основные эндпоинты датчиков
    path('data/', SensorDataView.as_view(), name='sensor_data'),
    path('alerts/', AlertListView.as_view(), name='alert_list'),
    path('alerts/<int:alert_id>/acknowledge/', AcknowledgeAlertView.as_view(), name='acknowledge_alert'),
    
    # Управление настройками устройств
    path('device/<int:device_id>/settings/', DeviceSettingsView.as_view(), name='device_settings'),
    path('device/<int:device_id>/status/', DeviceStatusView.as_view(), name='device_status'),
    
    # Административные функции
    path('buffer/cleanup/', BufferCleanupView.as_view(), name='buffer_cleanup'),
    
    # Тестирование
    path('test/', TestSensorView.as_view(), name='test_sensor'),
]