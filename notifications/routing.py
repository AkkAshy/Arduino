from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Для пользователей (мобильное приложение)
    re_path(r'ws/user/alerts/$', consumers.UserAlertConsumer.as_asgi()),
    
    # Для админ панели (веб дашборд)
    re_path(r'ws/admin/monitor/$', consumers.AdminMonitorConsumer.as_asgi()),
    
    # Для конкретного устройства
    re_path(r'ws/device/(?P<device_id>\w+)/$', consumers.DeviceConsumer.as_asgi()),
]