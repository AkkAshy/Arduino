# sensor/serializers.py - Исправленная версия с полной информацией о датчиках

from rest_framework import serializers
from .models import SensorData, Alert, SensorBuffer
from security.models import ArduinoDevice

class SensorDataSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)

    class Meta:
        model = SensorData
        fields = [
            'token', 'pir_motion', 'glass_break', 'door_open', 'panic_button',
            'triggered_sensors_count', 'is_valid_alert', 'work_time_status'
        ]
        read_only_fields = ['triggered_sensors_count', 'is_valid_alert', 'work_time_status']

class AlertSerializer(serializers.ModelSerializer):
    """Расширенный сериализатор для тревог с полной информацией о датчиках"""
    sensor_states = serializers.SerializerMethodField()
    triggered_sensors_display = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id', 'alert_type', 'timestamp', 'is_acknowledged',
            'device_name', 'device_address',
            'owner_username', 'owner_full_name', 'owner_phone',
            'triggered_sensors', 'sensors_count', 'confidence_level',
            'sensor_states', 'triggered_sensors_display', 'time_elapsed'
        ]
        read_only_fields = ['id', 'timestamp']

    def get_sensor_states(self, obj):
        """Полная информация о состоянии всех датчиков (true/false)"""
        # Если есть связанные данные датчиков, берем оттуда
        if obj.sensor_data:
            return {
                'pir_motion': obj.sensor_data.pir_motion,
                'glass_break': obj.sensor_data.glass_break,
                'door_open': obj.sensor_data.door_open,
                'panic_button': obj.sensor_data.panic_button
            }

        # Иначе восстанавливаем из triggered_sensors
        all_sensors = {
            'pir_motion': False,
            'glass_break': False,
            'door_open': False,
            'panic_button': False
        }

        # Устанавливаем true для сработавших датчиков
        for sensor in obj.triggered_sensors:
            if sensor in all_sensors:
                all_sensors[sensor] = True

        return all_sensors

    def get_triggered_sensors_display(self, obj):
        """Человекочитаемые названия только сработавших датчиков на узбекском"""
        sensor_names = {
            'pir_motion': '🚶 Harakat',
            'glass_break': '🔨 Shisha sinishi',
            'door_open': '🚪 Eshik ochilishi',
            'panic_button': '🚨 Favqulodda tugma'
        }
        return [sensor_names.get(sensor, sensor) for sensor in obj.triggered_sensors]

    def get_time_elapsed(self, obj):
        """Точное время с момента создания тревоги"""
        from django.utils import timezone

        now = timezone.now()
        elapsed = now - obj.timestamp

        # Общее количество секунд с момента создания
        total_seconds = int(elapsed.total_seconds())

        if total_seconds < 0:
            return "только что"
        elif total_seconds < 60:
            return f"{total_seconds} сек. назад"
        elif total_seconds < 3600:  # Меньше часа
            minutes = total_seconds // 60
            return f"{minutes} мин. назад"
        elif total_seconds < 86400:  # Меньше дня
            hours = total_seconds // 3600
            remaining_minutes = (total_seconds % 3600) // 60
            if remaining_minutes > 0:
                return f"{hours} ч. {remaining_minutes} мин. назад"
            else:
                return f"{hours} ч. назад"
        else:  # Больше дня
            days = elapsed.days
            hours = (total_seconds % 86400) // 3600
            if hours > 0:
                return f"{days} дн. {hours} ч. назад"
            else:
                return f"{days} дн. назад"

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
            'panic_button', 'is_processed', 'created_alert'
        ]