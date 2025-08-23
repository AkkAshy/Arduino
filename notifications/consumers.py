import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from security.models import ArduinoDevice, CustomUser
from sensor.models import Alert
import logging

logger = logging.getLogger(__name__)

class UserAlertConsumer(AsyncWebsocketConsumer):
    """WebSocket для пользователей мобильного приложения"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser:
            await self.close()
            return
        
        # Присоединяемся к группе уведомлений пользователя
        self.user_group_name = f'user_alerts_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем статус подключения
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'user_id': self.user.id,
            'username': self.user.username,
            'message': f'Подключен к уведомлениям пользователя {self.user.full_name}'
        }))
        
        logger.info(f"User {self.user.username} connected to alerts WebSocket")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info(f"User {getattr(self.user, 'username', 'Unknown')} disconnected from alerts WebSocket")

    async def receive(self, text_data):
        """Обработка сообщений от клиента"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
                
            elif message_type == 'get_unread_count':
                count = await self.get_unread_alerts_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': count
                }))
                
            elif message_type == 'acknowledge_alert':
                alert_id = text_data_json.get('alert_id')
                if alert_id:
                    success = await self.acknowledge_alert(alert_id)
                    await self.send(text_data=json.dumps({
                        'type': 'acknowledge_result',
                        'alert_id': alert_id,
                        'success': success
                    }))
                    
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def new_alert(self, event):
        """Отправка нового уведомления пользователю"""
        await self.send(text_data=json.dumps({
            'type': 'new_alert',
            'alert': event['alert_data'],
            'device': event['device_data'],
            'priority': event.get('priority', 'medium'),
            'sound': event.get('sound', True)
        }))

    async def alert_update(self, event):
        """Обновление статуса уведомления"""
        await self.send(text_data=json.dumps({
            'type': 'alert_update',
            'alert_id': event['alert_id'],
            'status': event['status'],
            'updated_by': event.get('updated_by')
        }))

    async def device_status_update(self, event):
        """Обновление статуса устройства"""
        await self.send(text_data=json.dumps({
            'type': 'device_status',
            'device_id': event['device_id'],
            'device_name': event['device_name'],
            'status': event['status'],
            'last_seen': event.get('last_seen')
        }))

    @database_sync_to_async
    def get_unread_alerts_count(self):
        return Alert.objects.filter(
            owner_id=self.user.id,
            is_acknowledged=False
        ).count()

    @database_sync_to_async
    def acknowledge_alert(self, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id, owner_id=self.user.id)
            alert.is_acknowledged = True
            alert.save()
            return True
        except Alert.DoesNotExist:
            return False


class AdminMonitorConsumer(AsyncWebsocketConsumer):
    """WebSocket для админ панели мониторинга"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        # Проверяем права администратора
        if self.user == AnonymousUser or not self.user.is_staff:
            await self.close()
            return
        
        # Присоединяемся к группе админ мониторинга
        self.admin_group_name = 'admin_monitor'
        
        await self.channel_layer.group_add(
            self.admin_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Отправляем статистику при подключении
        stats = await self.get_dashboard_stats()
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'admin_user': self.user.username,
            'dashboard_stats': stats
        }))
        
        logger.info(f"Admin {self.user.username} connected to monitor WebSocket")

    async def disconnect(self, close_code):
        if hasattr(self, 'admin_group_name'):
            await self.channel_layer.group_discard(
                self.admin_group_name,
                self.channel_name
            )
        logger.info(f"Admin {getattr(self.user, 'username', 'Unknown')} disconnected from monitor WebSocket")

    async def receive(self, text_data):
        """Обработка команд от админ панели"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'get_stats':
                stats = await self.get_dashboard_stats()
                await self.send(text_data=json.dumps({
                    'type': 'dashboard_stats',
                    'stats': stats
                }))
                
            elif message_type == 'bulk_acknowledge':
                alert_ids = text_data_json.get('alert_ids', [])
                count = await self.bulk_acknowledge_alerts(alert_ids)
                await self.send(text_data=json.dumps({
                    'type': 'bulk_acknowledge_result',
                    'acknowledged_count': count,
                    'alert_ids': alert_ids
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def new_alert_global(self, event):
        """Глобальное уведомление о новой тревоге для админов"""
        await self.send(text_data=json.dumps({
            'type': 'new_alert_global',
            'alert': event['alert_data'],
            'device': event['device_data'],
            'user': event['user_data'],
            'priority': event.get('priority', 'medium'),
            'location': event.get('location')
        }))

    async def stats_update(self, event):
        """Обновление статистики"""
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))

    @database_sync_to_async
    def get_dashboard_stats(self):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total_alerts = Alert.objects.count()
        unacknowledged = Alert.objects.filter(is_acknowledged=False).count()
        today_alerts = Alert.objects.filter(timestamp__gte=today_start).count()
        
        # Активные устройства
        active_devices = ArduinoDevice.objects.filter(
            is_active=True,
            user__isnull=False
        ).count()
        
        return {
            'total_alerts': total_alerts,
            'unacknowledged_alerts': unacknowledged,
            'alerts_today': today_alerts,
            'active_devices': active_devices,
            'last_updated': now.isoformat()
        }

    @database_sync_to_async
    def bulk_acknowledge_alerts(self, alert_ids):
        return Alert.objects.filter(id__in=alert_ids).update(is_acknowledged=True)


class DeviceConsumer(AsyncWebsocketConsumer):
    """WebSocket для конкретного устройства"""
    
    async def connect(self):
        self.device_id = self.scope['url_route']['kwargs']['device_id']
        self.user = self.scope["user"]
        
        if self.user == AnonymousUser:
            await self.close()
            return
            
        # Проверяем права доступа к устройству
        has_access = await self.check_device_access()
        if not has_access:
            await self.close()
            return
        
        self.device_group_name = f'device_{self.device_id}'
        
        await self.channel_layer.group_add(
            self.device_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'device_id': self.device_id
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'device_group_name'):
            await self.channel_layer.group_discard(
                self.device_group_name,
                self.channel_name
            )

    async def sensor_data_update(self, event):
        """Обновление данных датчиков в реальном времени"""
        await self.send(text_data=json.dumps({
            'type': 'sensor_data',
            'device_id': event['device_id'],
            'sensor_data': event['sensor_data'],
            'timestamp': event['timestamp']
        }))

    async def device_alert(self, event):
        """Уведомление о тревоге для конкретного устройства"""
        await self.send(text_data=json.dumps({
            'type': 'device_alert',
            'alert': event['alert_data']
        }))

    @database_sync_to_async
    def check_device_access(self):
        try:
            device = ArduinoDevice.objects.get(id=self.device_id)
            return device.user == self.user or self.user.is_staff
        except ArduinoDevice.DoesNotExist:
            return False