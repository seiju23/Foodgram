import base64

from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db.models import F
from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator

from recipes.models import (
    Recipe, Ingredient, Tag, IngredientAmount,
    Favorite, ShoppingCart)
from .utils import validate_tags_ingredients
from .validators import validate_username, validate_email
from users.models import User, Follow


MIN_COOKING_TIME = 1


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя."""
    username = serializers.CharField(
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            validate_username
        ],
        required=True,
        max_length=150,
    )
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all()),
            validate_email
        ]
    )

    def validate(self, data):
        user = User(**data)
        password = data.get('password')
        try:
            validate_password(password=password, user=user)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return super(UserSerializer, self).validate(data)

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    class Meta:
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name',
            'password'
        )
        model = User
        extra_kwargs = {'password': {'write_only': True}}


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
        if (self.context.get('request')
           and not self.context['request'].user.is_anonymous):
            return Follow.objects.filter(
                user=self.context['request'].user,
                author=obj).exists()
        return False


class FollowListSerializer(UserReadSerializer):
    """"Сериализатор для предоставления информации
    о подписках пользователя.
    """
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count'
        )
        read_only_fields = (
            'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = None
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = obj.recipes.all()[:int(recipes_limit)]
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


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменение пароля пользователя."""
    current_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate(self, obj):
        try:
            validate_password(obj['new_password'])
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(
                {'new_password': list(e.messages)}
            )
        return super().validate(obj)

    def update(self, instance, validated_data):
        if not instance.check_password(validated_data['current_password']):
            raise serializers.ValidationError(
                {'current_password': 'Неверный пароль.'}
            )
        if (validated_data['current_password']
           == validated_data['new_password']):
            raise serializers.ValidationError(
                {'new_password': 'Пароль совпадает с предыдущим.'}
            )
        instance.set_password(validated_data['new_password'])
        instance.save()
        return validated_data


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


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для связующего класса ингредиентов и рецептов."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientAmount
        fields = (
            'id', 'name',
            'measurement_unit',
        )


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
    author = UserReadSerializer(read_only=True)
    ingredients = IngredientAmountCreateSerializer(many=True)
    tags = TagSerializer(many=True, read_only=True)
    image = Base64ImageField(required=True, allow_null=False)
    cooking_time = serializers.IntegerField(
        validators=(
            MinValueValidator(
                limit_value=MIN_COOKING_TIME,
                message=(f'Величина должна быть не меньше {MIN_COOKING_TIME}')
            ),
        )
    )

    class Meta:
        fields = (
            'ingredients', 'author',
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
                'author': self.context.get('request').user,
            }
        )
        return data

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(
                id=ingredient_data.get('id'))
            IngredientAmount.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=ingredient_data.get('amount'),
            )
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
        super().update(instance, validated_data)
        for ingredient_data in ingredients_data:
            ingredient = Ingredient.objects.get(
                id=ingredient_data.get('id'))
            IngredientAmount.objects.create(
                recipe=instance,
                ingredient=ingredient,
                amount=ingredient_data.get('amount'),
            )
        instance.save()
        return instance

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeReadSerializer(
            instance,
            context={'request': request}
        ).data


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""
    ingredients = IngredientAmountSerializer(many=True)
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
            'id', 'name', 'measurement_unit', amount=F('recipe__amount')
        )
        return ingredients

    def get_is_favorited(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Favorite.objects.filter(
                user=self.context['request'].user,
                recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and ShoppingCart.objects.filter(
                user=self.context['request'].user,
                recipe=obj).exists()
        )


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""
    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном'
            )
        ]

    def validate(self, recipe):
        if not Recipe.objects.filter(id=recipe['id']).exists():
            raise serializers.ValidationError('Рецепт не существует')

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""
    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в списке покупок'
            )
        ]

    def validate(self, recipe):
        if not Recipe.objects.filter(id=recipe['id']).exists():
            raise serializers.ValidationError('Рецепт не существует')

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': request}
        ).data
