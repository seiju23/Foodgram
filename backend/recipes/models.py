from colorfield.fields import ColorField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from . import constants
from users.models import User


class Tag(models.Model):
    """Класс тегов."""
    name = models.CharField(
        'Тег', max_length=constants.MAX_LENGTH_TAG_NAME,
        blank=False, unique=True)
    slug = models.SlugField(
        'Slug', max_length=constants.MAX_LENGTH_TAG_SLUG,
        blank=False, unique=True)
    color = ColorField(format="hexa")

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Класс ингредиентов."""
    name = models.CharField(max_length=constants.MAX_LENGTH_INGREDIENT_NAME)
    measurement_unit = models.CharField(
        max_length=constants.MAX_LENGTH_INGREDIENT_UNIT)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """Класс рецептов."""
    name = models.CharField(max_length=constants.MAX_LENGTH_RECIPE_NAME)
    text = models.TextField()
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, 'Время готовки не может быть менее 1 минуты'),
            MaxValueValidator(300, 'Время готовки не должно превышать 5 часов')
        ])
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientAmount',
    )
    image = models.ImageField(
        upload_to='recipes/', null=False, blank=False)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name

    def get_tags(self):
        return ",".join([str(p) for p in self.tags.all()])

    def get_ingredients(self):
        return ",".join([str(p) for p in self.ingredients.all()])


class IngredientAmount(models.Model):
    """Класс для связи рецептов с ингредиентами."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipeingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, 'Количество не может быть меньше 1'),
            MaxValueValidator(100, 'Количество не может превышать 100')
            ])

    class Meta:
        verbose_name_plural = 'Количество ингредиентов'
        ordering = ['recipe']

    def __str__(self):
        return f'Для рецепта необходимо {self.amount} {self.ingredient}'


class Favorite(models.Model):
    """"Модель избранного."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
    )

    class Meta:
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"
        ordering = ['user']

    def __str__(self):
        return f'{self.user} добавил в избранное {self.recipe}'


class ShoppingCart(models.Model):
    """Модель списка покупок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shoppings_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shoppings_cart',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        ordering = ['user']

    def __str__(self):
        return f'{self.user} добавил в корзину {self.recipe}'
