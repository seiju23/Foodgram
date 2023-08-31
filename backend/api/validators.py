from rest_framework import serializers
import re


def validate_username(value):
    if value.lower() == "me":
        raise serializers.ValidationError("Username 'me' не подходит")
    pattern = r'^[\w.@=-]{1,150}$'
    if re.search(pattern, value) is None:
        raise serializers.ValidationError("Недопустимые символы в нике")
    return value


def validate_email(value):
    if len(value) > 254:
        raise serializers.ValidationError(
            'Поле email не может быть более 254 символов!')
    if not value:
        raise serializers.ValidationError(
            'Поле email не может быть пустым!')
    return value
