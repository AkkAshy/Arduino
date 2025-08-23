from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, ArduinoDevice
import secrets

# 👤 Регистрация пользователя
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = CustomUser
        fields = ['username', 'full_name', 'phone_number', 'password']

    def create(self, validated_data):
        user = CustomUser(
            username=validated_data['username'],
            full_name=validated_data['full_name'],
            phone_number=validated_data['phone_number']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def to_representation(self, instance):
        return {
            "id": instance.id,
            "username": instance.username,
            "full_name": instance.full_name,
            "phone_number": instance.phone_number,
        }

# 🔐 Авторизация пользователя (если нужно отдельно)
class UserAuthSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['username'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        data['user'] = user
        return data

# 🔌 Список Arduino-устройств
class ArduinoDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArduinoDevice
        fields = ['id', 'name', 'token', 'address', 'is_active', 'created_at']
        read_only_fields = ['token', 'created_at']

# 🆕 Создание Arduino-устройства (только токен)
class ArduinoDeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArduinoDevice
        fields = ['id', 'token']
        read_only_fields = ['id', 'token']

    def create(self, validated_data):
        validated_data['token'] = secrets.token_hex(8)
        return super().create(validated_data)

# ✏️ Обновление Arduino-устройства
class ArduinoDeviceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArduinoDevice
        fields = ['name', 'address', 'is_active']
