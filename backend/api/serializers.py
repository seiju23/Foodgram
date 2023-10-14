import base64

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import F
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from . import constants
from recipes.models import (
    Recipe, Ingredient, Tag, IngredientAmount,
    Favorite, ShoppingCart)
from .utils import validate_tags_ingredients
from users.constants import MAX_LENGTH_PASSWORD
from users.models import Follow


User = get_user_model()


class UserSignUpSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователей."""
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )

    def validate_password(self, password):
        if len(password) > MAX_LENGTH_PASSWORD:
            raise serializers.ValidationError(
                f'Длина пароля не должна превышать {MAX_LENGTH_PASSWORD}'
            )
        return password


class UserReadSerializer(UserSerializer):
    """Сериализатор для чтения пользователей."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        return (self.context.get('request')
                and self.context.get('request').user.is_authenticated
                and Follow.objects.filter(
                    user=self.context['request'].user,
                    author=obj).exists())


class FollowListSerializer(UserReadSerializer):
    """"Сериализатор для предоставления информации
    о подписках пользователя.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserReadSerializer.Meta):
        model = User
        fields = UserReadSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = None
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            try:
                recipes = obj.recipes.all()[:int(recipes_limit)]
            except TypeError:
                return 'В recipes_limit должна быть строка'
        return RecipeShortSerializer(
            recipes, many=True,
            context={'request': request}
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки/отписки от пользователей."""
    class Meta:
        fields = '__all__'
        model = Follow
        validators = [UniqueTogetherValidator(
            queryset=Follow.objects.all(), fields=(
                'user', 'author'),
            message='Вы уже подписаны на этого автора.'
        )]

    def validate_author(self, author):
        if self.context.get('request').user != author:
            return author
        raise serializers.ValidationError(
            'Вы не можете подписаться на себя.'
        )

    def to_representation(self, instance):
        request = self.context.get('request')
        return FollowListSerializer(
            instance.author, context={'request': request}
        ).data


class Base64ImageField(serializers.ImageField):
    """Класс для картинок с кодировкой Base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientAmountCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов при создании рецепта."""
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientAmount
        fields = ('id', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = '__all__'
        read_only_fields = ('id', 'name', 'color', 'slug',)


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов в избранном и корзине."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи рецептов."""
    ingredients = IngredientAmountCreateSerializer(many=True)
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        validators=(
            MinValueValidator(
                limit_value=constants.MIN_COOKING_TIME,
                message=(
                    f'Величина должна быть не меньше'
                    f'{constants.MIN_COOKING_TIME}')
            ),
            MaxValueValidator(
                limit_value=constants.MAX_COOKING_TIME,
                message=(
                    f'Величина не должна превышать'
                    f'{constants.MAX_COOKING_TIME}'
                )
            )
        )
    )

    class Meta:
        fields = (
            'ingredients',
            'name', 'text', 'cooking_time',
            'tags', 'image'
        )
        model = Recipe

    def validate(self, data):
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')
        fields = ['name', 'text', 'cooking_time']
        for field in fields:
            if not data.get(field):
                raise serializers.ValidationError(
                    'Поля должны быть заполнены.')
        if not tags or not ingredients:
            raise serializers.ValidationError('Не переданы нужные данные.')
        validate_tags_ingredients(tags, ingredients)
        data.update(
            {
                'tags': tags,
                'ingredients': ingredients,
            }
        )
        return data

    def create_ingredients(self, recipe, ingredients_data):
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                recipe=recipe,
                ingredient=Ingredient.objects.get(
                    id=ingredient_data.get('id')),
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        )

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(recipe, ingredients_data)
        recipe.tags.set(tags)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            "cooking_time", instance.cooking_time)
        IngredientAmount.objects.filter(
            recipe=instance).delete()
        instance.tags.clear()
        instance.tags.set(tags)
        self.create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeReadSerializer(
            instance,
            context={'request': request}
        ).data


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    author = UserReadSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text', 'ingredients',
            'tags', 'cooking_time', 'is_favorited',
            'is_in_shopping_cart'
        )

    def get_ingredients(self, recipe):
        ingredients = recipe.ingredients.values(
            'id', 'name',
            'measurement_unit', amount=F('ingredientamount__amount')
        )
        return ingredients

    def get_is_favorited(self, obj):
        return (
            self.context.get('request')
            and self.context.get('request').user.is_authenticated
            and Favorite.objects.filter(
                user=self.context['request'].user,
                recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return (
            self.context.get('request')
            and self.context.get('request').user.is_authenticated
            and ShoppingCart.objects.filter(
                user=self.context['request'].user,
                recipe=obj).exists()
        )


class FavCartMixin:
    """Миксин для избранного и списка покупок"""
    class Meta:
        validators = [
            UniqueTogetherValidator(
                queryset=None,
                fields=('user', 'recipe'),
                message=''
            )
        ]

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class FavoriteSerializer(FavCartMixin, serializers.ModelSerializer):
    """Сериализатор для избранного."""
    class Meta(FavCartMixin.Meta):
        model = Favorite
        fields = '__all__'
        FavCartMixin.Meta.validators[0].queryset = Favorite.objects.all()
        FavCartMixin.Meta.validators[0].message = 'Рецепт уже в избранном'


class ShoppingCartSerializer(FavCartMixin, serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    class Meta(FavCartMixin.Meta):
        model = ShoppingCart
        fields = '__all__'
        FavCartMixin.Meta.validators[0].queryset = ShoppingCart.objects.all()
        FavCartMixin.Meta.validators[0].message = 'Рецепт уже в списке покупок'
