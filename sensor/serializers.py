from rest_framework import serializers
from .models import SensorData, Alert, SensorBuffer
from security.models import ArduinoDevice

class SensorDataSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)
    
    class Meta:
        model = SensorData
        fields = [
            'token', 'pir_motion', 'glass_break', 'door_open', 'panic_button', 
            'temperature', 'humidity', 'triggered_sensors_count', 'is_valid_alert', 
            'work_time_status'
        ]
        read_only_fields = ['triggered_sensors_count', 'is_valid_alert', 'work_time_status']

class AlertSerializer(serializers.ModelSerializer):
    """Расширенный сериализатор для тревог"""
    triggered_sensors_display = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'timestamp', 'is_acknowledged',
            'device_name', 'device_address',
            'owner_username', 'owner_full_name', 'owner_phone',
            'triggered_sensors', 'sensors_count', 'confidence_level',
            'triggered_sensors_display', 'time_elapsed'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_triggered_sensors_display(self, obj):
        """Человекочитаемые названия датчиков"""
        sensor_names = {
            'pir_motion': '🚶 Движение',
            'glass_break': '🔨 Разбитие стекла',
            'door_open': '🚪 Открытие двери',
            'panic_button': '🚨 Паническая кнопка'
        }
        return [sensor_names.get(sensor, sensor) for sensor in obj.triggered_sensors]
    
    def get_time_elapsed(self, obj):
        """Время с момента создания тревоги"""
        from django.utils import timezone
        
        elapsed = timezone.now() - obj.timestamp
        
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

class DeviceSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор для настроек устройства"""
    work_start_time = serializers.TimeField(format='%H:%M')
    work_end_time = serializers.TimeField(format='%H:%M')
    current_work_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ArduinoDevice
        fields = [
            'id', 'name', 'work_schedule_enabled', 'work_start_time', 'work_end_time',
            'multi_sensor_required', 'sensor_count_threshold', 'time_window_seconds',
            'timezone_name', 'current_work_status'
        ]
    
    def get_current_work_status(self, obj):
        return obj.is_work_time_now()

class SensorBufferSerializer(serializers.ModelSerializer):
    """Сериализатор для буферных данных"""
    class Meta:
        model = SensorBuffer
        fields = [
            'id', 'timestamp', 'pir_motion', 'glass_break', 'door_open', 
            'panic_button', 'temperature', 'humidity', 'is_processed', 'created_alert'
        ]
