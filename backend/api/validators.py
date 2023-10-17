from rest_framework import serializers


def validate_username(value):
    if value.lower() == "me":
        raise serializers.ValidationError("Username 'me' не подходит")
    return value
