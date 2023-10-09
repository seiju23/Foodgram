from rest_framework import serializers

from recipes.models import Ingredient, Tag


def validate_tags_ingredients(tags, ingredients):
    ingredients_list = []
    tags_list = []
    for ingredient in ingredients:
        if ingredient.get('amount') <= 0 or ingredient.get('amount') > 100:
            raise serializers.ValidationError(
                'Количество не может быть меньше 1 и больше 100.'
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
