from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Ingredient, Tag


def create_object_util(request, instance, serializer_name):
    """Функция для создания объекта избранного или списка покупок."""
    serializer = serializer_name(
        data={'user': request.user.id, 'recipe': instance.id, },
        context={'request': request}
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


def delete_object_util(request, model_name, instance, error_message):
    """Функция для создания объекта избранного или списка покупок.
    """
    if not model_name.objects.filter(
        user=request.user,
        recipe=instance
    ).exists():
        return Response(
            {'errors': error_message},
            status=status.HTTP_400_BAD_REQUEST)
    model_name.objects.filter(user=request.user, recipe=instance).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def validate_tags_ingredients(tags, ingredients):
    ingredients_list = []
    tags_list = []
    for ingredient in ingredients:
        if ingredient.get('amount') <= 0:
            raise serializers.ValidationError(
                'Количество не может быть меньше 1'
            )
        if not Ingredient.objects.filter(id=ingredient.get('id')).exists():
            raise serializers.ValidationError(
                'Вы пытаетесь добавить несуществующий ингредиент.')
        ingredients_list.append(ingredient.get('id'))
    for tag_id in tags:
        if not Tag.objects.filter(id=tag_id).exists():
            raise serializers.ValidationError(
                'Вы пытаетесь добавить несуществующий тег.'
            )
        tags_list.append(tag_id)
    if len(tags_list) != len(set(tags_list)):
        raise serializers.ValidationError(
            'Теги должны быть уникальны.')
    if len(ingredients_list) != len(set(ingredients_list)):
        raise serializers.ValidationError(
            'Ингредиенты должны быть уникальны.')
    return True
