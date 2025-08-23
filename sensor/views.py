from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import SensorData, Alert, SensorBuffer
from .serializers import SensorDataSerializer, AlertSerializer
from .services import SensorDataProcessor
from security.models import ArduinoDevice
from notifications.utils import send_user_alert_notification, send_device_status_update, send_stats_update
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class SensorDataView(APIView):
    """Обновленный view с WebSocket уведомлениями"""
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = ArduinoDevice.objects.get(token=token, is_active=True)
        except ArduinoDevice.DoesNotExist:
            return Response(
                {'error': 'Invalid or inactive device token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        sensor_data_dict = {
            'pir_motion': request.data.get('pir_motion', False),
            'glass_break': request.data.get('glass_break', False),
            'door_open': request.data.get('door_open', False),
            'panic_button': request.data.get('panic_button', False),
            'temperature': request.data.get('temperature'),
            'humidity': request.data.get('humidity'),
        }
        
        try:
            processing_result = SensorDataProcessor.process_sensor_data(device, sensor_data_dict)
            
            # 🔔 WebSocket уведомления!
            if processing_result['alerts_created']:
                # Отправляем уведомления для каждой созданной тревоги
                for alert_id in processing_result['alerts_created']:
                    send_user_alert_notification(alert_id)
                
                # Обновляем статистику в админ панели
                send_stats_update()
            
            # Отправляем обновление статуса устройства
            send_device_status_update(
                device.id, 
                'online', 
                timezone.now()
            )
            
            logger.info(
                f"Device {device.name} processed with {len(processing_result['alerts_created'])} alerts"
            )
            
            return Response({
                "status": "data received and processed",
                "device_name": device.name,
                "processing_status": processing_result['status'],
                "message": processing_result['message'],
                "alerts_created": processing_result['alerts_created'],
                "notifications_sent": len(processing_result['alerts_created']) > 0,
                "work_time_active": device.is_work_time_now(),
                "multi_sensor_mode": device.multi_sensor_required
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing sensor data for device {device.name}: {str(e)}")
            return Response(
                {'error': 'Internal processing error'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AcknowledgeAlertView(APIView):
    """Подтверждение оповещения с WebSocket уведомлением"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, alert_id):
        try:
            alert = Alert.objects.get(id=alert_id, owner_id=request.user.id)
            alert.is_acknowledged = True
            alert.save()
            
            # 🔔 WebSocket уведомление об изменении статуса
            from notifications.utils import send_alert_status_update
            send_alert_status_update(alert_id, 'acknowledged', request.user.username)
            
            # Обновляем статистику
            send_stats_update()
            
            return Response({
                "status": "alert acknowledged",
                "alert_id": alert_id,
                "alert_type": alert.alert_type,
                "sensors_count": alert.sensors_count,
                "acknowledged_by": request.user.username
            })
        except Alert.DoesNotExist:
            return Response(
                {"error": "Alert not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class AlertListView(APIView):
    """Получение списка оповещений пользователя"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Получаем только оповещения для устройств текущего пользователя
        user_alerts = Alert.objects.filter(owner_id=request.user.id)
        
        # Фильтры
        alert_type = request.query_params.get('type')
        acknowledged = request.query_params.get('acknowledged')
        confidence = request.query_params.get('confidence')
        
        if alert_type:
            user_alerts = user_alerts.filter(alert_type=alert_type)
        
        if acknowledged == 'true':
            user_alerts = user_alerts.filter(is_acknowledged=True)
        elif acknowledged == 'false':
            user_alerts = user_alerts.filter(is_acknowledged=False)
        
        if confidence:
            user_alerts = user_alerts.filter(confidence_level=confidence)
        
        serializer = AlertSerializer(user_alerts, many=True)
        return Response(serializer.data)



class DeviceSettingsView(APIView):
    """Управление настройками устройства"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, device_id):
        """Получить настройки устройства"""
        try:
            device = ArduinoDevice.objects.get(id=device_id, user=request.user)
            
            return Response({
                'id': device.id,
                'name': device.name,
                'work_schedule_enabled': device.work_schedule_enabled,
                'work_start_time': device.work_start_time.strftime('%H:%M'),
                'work_end_time': device.work_end_time.strftime('%H:%M'),
                'multi_sensor_required': device.multi_sensor_required,
                'sensor_count_threshold': device.sensor_count_threshold,
                'time_window_seconds': device.time_window_seconds,
                'timezone_name': device.timezone_name,
                'current_work_status': device.is_work_time_now()
            })
        except ArduinoDevice.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request, device_id):
        """Обновить настройки устройства"""
        try:
            device = ArduinoDevice.objects.get(id=device_id, user=request.user)
            
            # Обновляем настройки расписания
            if 'work_schedule_enabled' in request.data:
                device.work_schedule_enabled = request.data['work_schedule_enabled']
            
            if 'work_start_time' in request.data:
                from datetime import datetime
                device.work_start_time = datetime.strptime(
                    request.data['work_start_time'], '%H:%M'
                ).time()
            
            if 'work_end_time' in request.data:
                from datetime import datetime
                device.work_end_time = datetime.strptime(
                    request.data['work_end_time'], '%H:%M'
                ).time()
            
            # Обновляем настройки датчиков
            if 'multi_sensor_required' in request.data:
                device.multi_sensor_required = request.data['multi_sensor_required']
            
            if 'sensor_count_threshold' in request.data:
                threshold = int(request.data['sensor_count_threshold'])
                if 1 <= threshold <= 4:  # Максимум 4 типа датчиков
                    device.sensor_count_threshold = threshold
            
            if 'time_window_seconds' in request.data:
                window = int(request.data['time_window_seconds'])
                if 10 <= window <= 300:  # От 10 секунд до 5 минут
                    device.time_window_seconds = window
            
            device.save()
            
            return Response({
                'message': 'Device settings updated successfully',
                'current_work_status': device.is_work_time_now(),
                'updated_settings': {
                    'work_schedule_enabled': device.work_schedule_enabled,
                    'work_start_time': device.work_start_time.strftime('%H:%M'),
                    'work_end_time': device.work_end_time.strftime('%H:%M'),
                    'multi_sensor_required': device.multi_sensor_required,
                    'sensor_count_threshold': device.sensor_count_threshold,
                    'time_window_seconds': device.time_window_seconds
                }
            })
            
        except ArduinoDevice.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': f'Invalid value: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class DeviceStatusView(APIView):
    """Статус устройства в реальном времени"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, device_id):
        try:
            device = ArduinoDevice.objects.get(id=device_id, user=request.user)
            
            # Последние данные с датчиков
            latest_data = SensorData.objects.filter(device=device).first()
            
            # Количество необработанных сигналов в буфере
            pending_buffer_count = SensorBuffer.objects.filter(
                device=device, 
                is_processed=False
            ).count()
            
            # Статистика тревог за последние 24 часа
            from django.utils import timezone
            from datetime import timedelta
            
            yesterday = timezone.now() - timedelta(days=1)
            recent_alerts = Alert.objects.filter(
                device=device, 
                timestamp__gte=yesterday
            )
            
            return Response({
                'device_info': {
                    'id': device.id,
                    'name': device.name,
                    'is_active': device.is_active,
                    'work_time_active': device.is_work_time_now(),
                    'multi_sensor_mode': device.multi_sensor_required
                },
                'latest_sensor_data': {
                    'timestamp': latest_data.timestamp if latest_data else None,
                    'temperature': latest_data.temperature if latest_data else None,
                    'humidity': latest_data.humidity if latest_data else None,
                    'is_valid_alert': latest_data.is_valid_alert if latest_data else None
                },
                'buffer_status': {
                    'pending_signals': pending_buffer_count,
                    'threshold_needed': device.sensor_count_threshold,
                    'time_window': device.time_window_seconds
                },
                'recent_alerts': {
                    'total_24h': recent_alerts.count(),
                    'unacknowledged': recent_alerts.filter(is_acknowledged=False).count(),
                    'by_confidence': {
                        'high': recent_alerts.filter(confidence_level='high').count(),
                        'medium': recent_alerts.filter(confidence_level='medium').count(),
                        'low': recent_alerts.filter(confidence_level='low').count()
                    }
                }
            })
            
        except ArduinoDevice.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class BufferCleanupView(APIView):
    """Очистка буферных данных (admin only)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Проверяем права администратора
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        deleted_count = SensorDataProcessor.cleanup_old_buffer_data()
        
        return Response({
            'message': f'Cleaned up {deleted_count} old buffer entries',
            'deleted_count': deleted_count
        })

class TestSensorView(APIView):
    """Тестовый эндпоинт для проверки логики датчиков"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        device_token = request.data.get('token')
        test_scenario = request.data.get('scenario', 'single')
        
        if not device_token:
            return Response(
                {'error': 'Device token required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            device = ArduinoDevice.objects.get(token=device_token, user=request.user)
        except ArduinoDevice.DoesNotExist:
            return Response(
                {'error': 'Device not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Различные тестовые сценарии
        test_scenarios = {
            'single': {
                'pir_motion': True,
                'glass_break': False,
                'door_open': False,
                'panic_button': False,
                'temperature': 23.5,
                'humidity': 65.0
            },
            'multi': {
                'pir_motion': True,
                'glass_break': True,
                'door_open': False,
                'panic_button': False,
                'temperature': 24.1,
                'humidity': 68.2
            },
            'panic': {
                'pir_motion': False,
                'glass_break': False,
                'door_open': False,
                'panic_button': True,
                'temperature': 22.8,
                'humidity': 67.5
            },
            'all_sensors': {
                'pir_motion': True,
                'glass_break': True,
                'door_open': True,
                'panic_button': False,
                'temperature': 25.0,
                'humidity': 70.0
            }
        }
        
        if test_scenario not in test_scenarios:
            return Response(
                {'error': 'Invalid test scenario'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sensor_data = test_scenarios[test_scenario]
        
        # Обрабатываем тестовые данные
        processing_result = SensorDataProcessor.process_sensor_data(device, sensor_data)
        
        return Response({
            'test_scenario': test_scenario,
            'device_name': device.name,
            'device_settings': {
                'work_time_active': device.is_work_time_now(),
                'multi_sensor_required': device.multi_sensor_required,
                'sensor_threshold': device.sensor_count_threshold,
                'time_window': device.time_window_seconds
            },
            'test_data': sensor_data,
            'processing_result': processing_result
        })
