from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from sensor.models import Alert, SensorData
from security.models import ArduinoDevice, CustomUser
from .serializers import AlertMonitorSerializer, AlertStatsSerializer

class AlertMonitorListView(APIView):
    """Получение всех тревог для мониторинга"""
    permission_classes = [IsAuthenticated]  # Можно изменить на IsAdminUser для админов
    
    def get(self, request):
        # Параметры фильтрации
        alert_type = request.query_params.get('type')
        acknowledged = request.query_params.get('acknowledged')
        device_id = request.query_params.get('device_id')
        owner_id = request.query_params.get('owner_id')
        limit = int(request.query_params.get('limit', 50))
        
        # Базовый queryset
        alerts = Alert.objects.all().order_by('-timestamp')
        
        # Применяем фильтры
        if alert_type:
            alerts = alerts.filter(alert_type=alert_type)
        
        if acknowledged == 'true':
            alerts = alerts.filter(is_acknowledged=True)
        elif acknowledged == 'false':
            alerts = alerts.filter(is_acknowledged=False)
        
        if device_id:
            alerts = alerts.filter(device_id=device_id)
        
        if owner_id:
            alerts = alerts.filter(owner_id=owner_id)
        
        # Ограничиваем количество
        alerts = alerts[:limit]
        
        serializer = AlertMonitorSerializer(alerts, many=True)
        return Response(serializer.data)

class AlertStatsView(APIView):
    """Статистика тревог"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Общая статистика
        total_alerts = Alert.objects.count()
        unacknowledged_alerts = Alert.objects.filter(is_acknowledged=False).count()
        alerts_today = Alert.objects.filter(timestamp__gte=today_start).count()
        
        # Статистика по типам тревог
        alerts_by_type = dict(
            Alert.objects.values('alert_type')
            .annotate(count=Count('id'))
            .values_list('alert_type', 'count')
        )
        
        # Самое активное устройство
        most_active = (
            Alert.objects.values('device_name')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )
        most_active_device = most_active['device_name'] if most_active else 'Нет данных'
        
        # Время последней тревоги
        latest_alert = Alert.objects.order_by('-timestamp').first()
        latest_alert_time = latest_alert.timestamp if latest_alert else None
        
        stats_data = {
            'total_alerts': total_alerts,
            'unacknowledged_alerts': unacknowledged_alerts,
            'alerts_today': alerts_today,
            'alerts_by_type': alerts_by_type,
            'most_active_device': most_active_device,
            'latest_alert_time': latest_alert_time
        }
        
        serializer = AlertStatsSerializer(stats_data)
        return Response(serializer.data)

class BulkAcknowledgeAlertsView(APIView):
    """Массовое подтверждение тревог"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        alert_ids = request.data.get('alert_ids', [])
        
        if not alert_ids:
            return Response(
                {'error': 'No alert IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Обновляем статус тревог
        updated_count = Alert.objects.filter(
            id__in=alert_ids
        ).update(is_acknowledged=True)
        
        return Response({
            'message': f'{updated_count} alerts acknowledged',
            'acknowledged_count': updated_count
        })

class AlertDetailView(APIView):
    """Детальная информация о конкретной тревоге"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id)
            serializer = AlertMonitorSerializer(alert)
            return Response(serializer.data)
        except Alert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, alert_id):
        """Обновление статуса тревоги"""
        try:
            alert = Alert.objects.get(id=alert_id)
            
            if 'is_acknowledged' in request.data:
                alert.is_acknowledged = request.data['is_acknowledged']
                alert.save()
            
            serializer = AlertMonitorSerializer(alert)
            return Response(serializer.data)
        except Alert.DoesNotExist:
            return Response(
                {'error': 'Alert not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ActiveDevicesView(APIView):
    """Список активных устройств"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        devices = ArduinoDevice.objects.filter(
            is_active=True,
            user__isnull=False
        ).select_related('user')
        
        device_data = []
        for device in devices:
            # Последняя активность устройства
            last_sensor_data = SensorData.objects.filter(
                device=device
            ).order_by('-timestamp').first()
            
            # Количество тревог за последний час
            hour_ago = timezone.now() - timedelta(hours=1)
            recent_alerts = Alert.objects.filter(
                device=device,
                timestamp__gte=hour_ago
            ).count()
            
            device_data.append({
                'id': device.id,
                'name': device.name or 'Unnamed Device',
                'address': device.address,
                'owner': {
                    'username': device.user.username,
                    'full_name': device.user.full_name,
                    'phone': device.user.phone_number
                },
                'last_activity': last_sensor_data.timestamp if last_sensor_data else None,
                'recent_alerts_count': recent_alerts,
                'status': 'online' if last_sensor_data and 
                         (timezone.now() - last_sensor_data.timestamp).seconds < 300 
                         else 'offline'
            })
        
        return Response(device_data)