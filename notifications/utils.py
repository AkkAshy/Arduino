from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sensor.models import Alert
from security.models import ArduinoDevice
import logging

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

def send_user_alert_notification(alert_id):
    """Отправка уведомления пользователю о новой тревоге"""
    try:
        alert = Alert.objects.select_related('device', 'device__user').get(id=alert_id)
        
        if not alert.device or not alert.device.user:
            return False
        
        # Данные для отправки
        alert_data = {
            'id': alert.id,
            'type': alert.alert_type,
            'timestamp': alert.timestamp.isoformat(),
            'triggered_sensors': alert.triggered_sensors,
            'sensors_count': alert.sensors_count,
            'confidence_level': alert.confidence_level,
            'is_acknowledged': alert.is_acknowledged
        }
        
        device_data = {
            'id': alert.device.id,
            'name': alert.device.name or 'Unnamed Device',
            'address': alert.device.address or 'No address'
        }
        
        # Определяем приоритет
        priority = 'high' if alert.alert_type == 'panic' else 'medium'
        if alert.confidence_level == 'high' or alert.sensors_count >= 3:
            priority = 'high'
        
        # Отправляем пользователю
        user_group = f'user_alerts_{alert.device.user.id}'
        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type': 'new_alert',
                'alert_data': alert_data,
                'device_data': device_data,
                'priority': priority,
                'sound': priority == 'high'
            }
        )
        
        # Отправляем в админ панель
        user_data = {
            'id': alert.device.user.id,
            'username': alert.device.user.username,
            'full_name': alert.device.user.full_name,
            'phone': alert.device.user.phone_number or 'No phone'
        }
        
        async_to_sync(channel_layer.group_send)(
            'admin_monitor',
            {
                'type': 'new_alert_global',
                'alert_data': alert_data,
                'device_data': device_data,
                'user_data': user_data,
                'priority': priority,
                'location': device_data['address']
            }
        )
        
        # Отправляем в группу устройства
        async_to_sync(channel_layer.group_send)(
            f'device_{alert.device.id}',
            {
                'type': 'device_alert',
                'alert_data': alert_data
            }
        )
        
        logger.info(f"Alert notification sent: {alert_id} to user {alert.device.user.username}")
        return True
        
    except Alert.DoesNotExist:
        logger.error(f"Alert not found: {alert_id}")
        return False
    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")
        return False

def send_device_status_update(device_id, status, last_seen=None):
    """Отправка обновления статуса устройства"""
    try:
        device = ArduinoDevice.objects.select_related('user').get(id=device_id)
        
        # Пользователю
        if device.user:
            async_to_sync(channel_layer.group_send)(
                f'user_alerts_{device.user.id}',
                {
                    'type': 'device_status_update',
                    'device_id': device_id,
                    'device_name': device.name or 'Unnamed Device',
                    'status': status,
                    'last_seen': last_seen.isoformat() if last_seen else None
                }
            )
        
        # В группу устройства
        async_to_sync(channel_layer.group_send)(
            f'device_{device_id}',
            {
                'type': 'sensor_data_update',
                'device_id': device_id,
                'sensor_data': {'status': status},
                'timestamp': last_seen.isoformat() if last_seen else None
            }
        )
        
        return True
        
    except ArduinoDevice.DoesNotExist:
        logger.error(f"Device not found: {device_id}")
        return False
    except Exception as e:
        logger.error(f"Error sending device status update: {e}")
        return False

def send_stats_update():
    """Отправка обновленной статистики админам"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        stats = {
            'total_alerts': Alert.objects.count(),
            'unacknowledged_alerts': Alert.objects.filter(is_acknowledged=False).count(),
            'alerts_today': Alert.objects.filter(timestamp__gte=today_start).count(),
            'active_devices': ArduinoDevice.objects.filter(is_active=True, user__isnull=False).count(),
            'last_updated': now.isoformat()
        }
        
        async_to_sync(channel_layer.group_send)(
            'admin_monitor',
            {
                'type': 'stats_update',
                'stats': stats
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending stats update: {e}")
        return False
    

def send_alert_status_update(alert_id, status, updated_by=None):
    """Отправка обновления статуса тревоги"""
    try:
        alert = Alert.objects.select_related('device', 'device__user').get(id=alert_id)
        
        # Пользователю
        if alert.device and alert.device.user:
            async_to_sync(channel_layer.group_send)(
                f'user_alerts_{alert.device.user.id}',
                {
                    'type': 'alert_update',
                    'alert_id': alert_id,
                    'status': status,
                    'updated_by': updated_by
                }
            )
        
        # Админам
        async_to_sync(channel_layer.group_send)(
            'admin_monitor',
            {
                'type': 'alert_update',
                'alert_id': alert_id,
                'status': status,
                'updated_by': updated_by
            }
        )
        
        return True
        
    except Alert.DoesNotExist:
        logger.error(f"Alert not found for status update: {alert_id}")
        return False
    except Exception as e:
        logger.error(f"Error sending alert status update: {e}")
        return False

def send_bulk_acknowledge_notification(alert_ids, updated_by):
    """Уведомление о массовом подтверждении"""
    try:
        # Админам
        async_to_sync(channel_layer.group_send)(
            'admin_monitor',
            {
                'type': 'bulk_acknowledge_result',
                'alert_ids': alert_ids,
                'acknowledged_count': len(alert_ids),
                'updated_by': updated_by
            }
        )
        
        # Затронутым пользователям
        affected_users = Alert.objects.filter(
            id__in=alert_ids
        ).values_list('owner_id', flat=True).distinct()
        
        for user_id in affected_users:
            user_alert_ids = list(Alert.objects.filter(
                id__in=alert_ids,
                owner_id=user_id
            ).values_list('id', flat=True))
            
            async_to_sync(channel_layer.group_send)(
                f'user_alerts_{user_id}',
                {
                    'type': 'bulk_acknowledge_result',
                    'alert_ids': user_alert_ids,
                    'acknowledged_count': len(user_alert_ids),
                    'updated_by': updated_by
                }
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending bulk acknowledge notification: {e}")
        return False
