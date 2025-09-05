# sensor/services.py - Полностью очищенная версия без temperature/humidity

from django.utils import timezone
from datetime import timedelta
from .models import SensorData, SensorBuffer, Alert
from security.models import ArduinoDevice
import logging

logger = logging.getLogger(__name__)

class SensorDataProcessor:
    """Сервис для умной обработки данных датчиков"""

    @staticmethod
    def process_sensor_data(device, sensor_data_dict):
        """
        Основная логика обработки данных с датчиков
        """
        # 1. Проверяем рабочее время
        if not device.is_work_time_now():
            logger.info(f"Device {device.name} is outside work schedule. Data ignored.")
            return {
                'status': 'ignored_schedule',
                'message': 'Outside work schedule',
                'alerts_created': []
            }

        # 2. Подготавливаем данные только для датчиков (без temperature/humidity)
        sensor_only_data = {
            'pir_motion': sensor_data_dict.get('pir_motion', False),
            'glass_break': sensor_data_dict.get('glass_break', False),
            'door_open': sensor_data_dict.get('door_open', False),
            'panic_button': sensor_data_dict.get('panic_button', False)
        }

        # 3. Сохраняем в буфер (только поля датчиков)
        buffer_entry = SensorBuffer.objects.create(
            device=device,
            **sensor_only_data
        )

        # 4. Проверяем паническую кнопку (всегда приоритет)
        if sensor_only_data.get('panic_button', False):
            return SensorDataProcessor._handle_panic_button(device, buffer_entry, sensor_only_data)

        # 5. Если включена многосенсорная проверка
        if device.multi_sensor_required:
            return SensorDataProcessor._handle_multi_sensor_logic(device, buffer_entry, sensor_only_data)
        else:
            # Обычная логика - любой датчик создает тревогу
            return SensorDataProcessor._handle_single_sensor_logic(device, buffer_entry, sensor_only_data)

    @staticmethod
    def _handle_panic_button(device, buffer_entry, sensor_data_dict):
        """Обработка паники - всегда создаем тревогу"""
        sensor_data = SensorData.objects.create(
            device=device,
            is_valid_alert=True,
            **sensor_data_dict  # Только поля датчиков
        )

        alert = Alert.objects.create(
            device=device,
            alert_type='panic',
            sensor_data=sensor_data,
            triggered_sensors=['panic_button'],
            sensors_count=1,
            confidence_level='high'
        )

        buffer_entry.is_processed = True
        buffer_entry.created_alert = True
        buffer_entry.save()

        logger.warning(f"PANIC ALERT created for device {device.name}")

        return {
            'status': 'panic_alert_created',
            'message': 'Panic button alert created immediately',
            'alerts_created': [alert.id]
        }

    @staticmethod
    def _handle_multi_sensor_logic(device, buffer_entry, sensor_data_dict):
        """Логика множественных датчиков"""
        time_window = timedelta(seconds=device.time_window_seconds)
        cutoff_time = timezone.now() - time_window

        # Получаем все необработанные сигналы за последние N секунд
        recent_buffer = SensorBuffer.objects.filter(
            device=device,
            timestamp__gte=cutoff_time,
            is_processed=False
        ).order_by('-timestamp')

        # Считаем уникальные типы датчиков за период
        triggered_sensor_types = set()

        for entry in recent_buffer:
            if entry.pir_motion:
                triggered_sensor_types.add('pir_motion')
            if entry.glass_break:
                triggered_sensor_types.add('glass_break')
            if entry.door_open:
                triggered_sensor_types.add('door_open')
            if entry.panic_button:
                triggered_sensor_types.add('panic_button')

        sensors_count = len(triggered_sensor_types)

        if sensors_count >= device.sensor_count_threshold:
            # Условие выполнено - создаем тревогу
            return SensorDataProcessor._create_multi_sensor_alert(
                device, recent_buffer, triggered_sensor_types, sensor_data_dict
            )
        else:
            # Условие не выполнено - просто сохраняем в буфер
            logger.info(
                f"Device {device.name}: {sensors_count}/{device.sensor_count_threshold} "
                f"sensors triggered. Waiting for more signals."
            )

            return {
                'status': 'waiting_for_more_sensors',
                'message': f'Need {device.sensor_count_threshold - sensors_count} more sensor types',
                'alerts_created': []
            }

    @staticmethod
    def _create_multi_sensor_alert(device, buffer_entries, triggered_sensor_types, latest_data):
        """Создание тревоги при срабатывании множественных датчиков"""
        # Создаем основную запись в SensorData
        sensor_data = SensorData.objects.create(
            device=device,
            is_valid_alert=True,
            **latest_data  # Только поля датчиков
        )

        # Определяем тип тревоги и уровень доверия
        if len(triggered_sensor_types) >= 3:
            confidence = 'high'
        elif len(triggered_sensor_types) >= 2:
            confidence = 'medium'
        else:
            confidence = 'low'

        # Выбираем основной тип тревоги
        if 'panic_button' in triggered_sensor_types:
            alert_type = 'panic'
        elif 'glass_break' in triggered_sensor_types:
            alert_type = 'glass'
        elif 'door_open' in triggered_sensor_types:
            alert_type = 'door'
        elif 'pir_motion' in triggered_sensor_types:
            alert_type = 'motion'
        else:
            alert_type = 'multi_sensor'

        # Создаем тревогу
        alert = Alert.objects.create(
            device=device,
            alert_type=alert_type,
            sensor_data=sensor_data,
            triggered_sensors=list(triggered_sensor_types),
            sensors_count=len(triggered_sensor_types),
            confidence_level=confidence
        )

        # Помечаем все буферные записи как обработанные
        buffer_entries.update(is_processed=True, created_alert=True)

        logger.warning(
            f"MULTI-SENSOR ALERT created for device {device.name}: "
            f"{len(triggered_sensor_types)} sensors triggered: {', '.join(triggered_sensor_types)}"
        )

        return {
            'status': 'multi_sensor_alert_created',
            'message': f'Alert created with {len(triggered_sensor_types)} sensors',
            'alerts_created': [alert.id],
            'triggered_sensors': list(triggered_sensor_types),
            'confidence': confidence
        }

    @staticmethod
    def _handle_single_sensor_logic(device, buffer_entry, sensor_data_dict):
        """Обычная логика - любой датчик создает тревогу"""
        triggered_sensors = []

        if sensor_data_dict.get('pir_motion'):
            triggered_sensors.append('pir_motion')
        if sensor_data_dict.get('glass_break'):
            triggered_sensors.append('glass_break')
        if sensor_data_dict.get('door_open'):
            triggered_sensors.append('door_open')
        if sensor_data_dict.get('panic_button'):
            triggered_sensors.append('panic_button')

        if not triggered_sensors:
            # Нет активных датчиков - просто сохраняем данные без тревоги
            SensorData.objects.create(device=device, **sensor_data_dict)
            buffer_entry.is_processed = True
            buffer_entry.save()

            return {
                'status': 'data_saved_no_alerts',
                'message': 'No sensors triggered',
                'alerts_created': []
            }

        # Создаем тревоги для каждого сработавшего датчика
        sensor_data = SensorData.objects.create(
            device=device,
            is_valid_alert=True,
            **sensor_data_dict  # Только поля датчиков
        )

        alerts_created = []

        for sensor_type in triggered_sensors:
            if sensor_type == 'pir_motion':
                alert_type = 'motion'
            elif sensor_type == 'glass_break':
                alert_type = 'glass'
            elif sensor_type == 'door_open':
                alert_type = 'door'
            elif sensor_type == 'panic_button':
                alert_type = 'panic'

            alert = Alert.objects.create(
                device=device,
                alert_type=alert_type,
                sensor_data=sensor_data,
                triggered_sensors=[sensor_type],
                sensors_count=1,
                confidence_level='medium'
            )
            alerts_created.append(alert.id)

        buffer_entry.is_processed = True
        buffer_entry.created_alert = True
        buffer_entry.save()

        return {
            'status': 'single_sensor_alerts_created',
            'message': f'{len(alerts_created)} alerts created',
            'alerts_created': alerts_created
        }

    @staticmethod
    def cleanup_old_buffer_data():
        """Очистка старых данных из буфера (запускать по расписанию)"""
        cutoff_time = timezone.now() - timedelta(hours=1)
        deleted_count = SensorBuffer.objects.filter(timestamp__lt=cutoff_time).delete()[0]

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old buffer entries")

        return deleted_count