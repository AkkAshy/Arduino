from rest_framework import serializers
from sensor.models import Alert, SensorData
from security.models import ArduinoDevice

class AlertMonitorSerializer(serializers.ModelSerializer):
    """Расширенный serializer для мониторинга тревог"""
    device_info = serializers.SerializerMethodField()
    owner_info = serializers.SerializerMethodField()
    sensor_details = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'timestamp', 'is_acknowledged',
            'device_name', 'device_address', 
            'owner_username', 'owner_full_name', 'owner_phone',
            'device_info', 'owner_info', 'sensor_details', 'time_elapsed'
        ]
    
    def get_device_info(self, obj):
        try:
            device = ArduinoDevice.objects.get(id=obj.device.id)
            return {
                'id': device.id,
                'name': device.name or 'Unnamed Device',
                'address': device.address or 'No address',
                'is_active': device.is_active,
                'created_at': device.created_at
            }
        except:
            return {
                'name': obj.device_name,
                'address': obj.device_address,
                'status': 'offline'
            }
    
    def get_owner_info(self, obj):
        return {
            'id': obj.owner_id,
            'username': obj.owner_username,
            'full_name': obj.owner_full_name,
            'phone': obj.owner_phone or 'No phone'
        }
    
    def get_sensor_details(self, obj):
        if obj.sensor_data:
            return {
                'temperature': obj.sensor_data.temperature,
                'humidity': obj.sensor_data.humidity,
                'pir_motion': obj.sensor_data.pir_motion,
                'glass_break': obj.sensor_data.glass_break,
                'door_open': obj.sensor_data.door_open,
                'panic_button': obj.sensor_data.panic_button
            }
        return None
    
    def get_time_elapsed(self, obj):
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        elapsed = now - obj.timestamp
        
        if elapsed.days > 0:
            return f"{elapsed.days} дн. назад"
        elif elapsed.seconds > 3600:
            hours = elapsed.seconds // 3600
            return f"{hours} ч. назад"
        elif elapsed.seconds > 60:
            minutes = elapsed.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"

class AlertStatsSerializer(serializers.Serializer):
    """Статистика тревог"""
    total_alerts = serializers.IntegerField()
    unacknowledged_alerts = serializers.IntegerField()
    alerts_today = serializers.IntegerField()
    alerts_by_type = serializers.DictField()
    most_active_device = serializers.CharField()
    latest_alert_time = serializers.DateTimeField()