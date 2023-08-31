from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models


User = get_user_model()


class Tag(models.Model):
    """Класс тегов."""
    name = models.CharField('Тег', max_length=50, null=False, unique=True)
    slug = models.SlugField('Slug', max_length=100, unique=True)
    color = models.CharField(
        verbose_name='Цвет',
        max_length=7,
        null=False,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Класс ингредиентов."""
    MEASURE_CHOICES = (
        ('мг', 'милиграмм'),
        ('г', 'грамм'),
        ('кг', 'килограмм')
    )
    name = models.CharField(max_length=100)
    measurement_unit = models.CharField(max_length=2, choices=MEASURE_CHOICES)

    class Meta:
        ordering = ['name']
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """Класс рецептов."""
    name = models.CharField(max_length=200, blank=False)
    text = models.TextField()
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='recipes')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    cooking_time = models.IntegerField(validators=[MinValueValidator(1)])
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientAmount',
    )
    image = models.ImageField(
        upload_to='recipes/', null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    is_favorited = models.BooleanField(default=False)
    is_in_shopping_cart = models.BooleanField(default=False)

    class Meta:
        ordering = ['-pub_date']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientAmount(models.Model):
    """Класс для связи рецептов с ингредиентами."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)])

    class Meta:
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        f'Для рецепта необходимо {self.amount} {self.ingredient}'


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
        related_name='favorite_recipes',
    )

    class Meta:
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"

    def __str__(self):
        return f'{self.user} добавил в избранное рецепт {self.recipe}'


class ShoppingCart(models.Model):
    """Модель списка покупок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_recipes',
    )

    class Meta:
        verbose_name = 'Список покупок'

    def __str__(self):
        return f'{self.user} добавил в список покупок {self.recipe}'
