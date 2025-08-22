from django.urls import path
from .views import SensorDataView, AlertListView, AcknowledgeAlertView

app_name = 'sensors'

urlpatterns = [
    # Эндпоинт для приема данных с датчиков Arduino
    path('data/', SensorDataView.as_view(), name='sensor_data'),
    
    # Эндпоинт для получения списка оповещений пользователя
    path('alerts/', AlertListView.as_view(), name='alert_list'),
    
    # Эндпоинт для подтверждения оповещения
    path('alerts/<int:alert_id>/acknowledge/', AcknowledgeAlertView.as_view(), name='acknowledge_alert'),
]
