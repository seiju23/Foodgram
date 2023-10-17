from django.contrib import admin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import TokenProxy

from . import models


class IngredientAmountAdmin(admin.ModelAdmin):
    list_display = ('pk', 'recipe', 'ingredient', 'amount')
    list_editable = ('recipe', 'ingredient', 'amount')


class RecipeTagInline(admin.TabularInline):
    model = models.Recipe.tags.through
    min_num = 1


class RecipeIngredientInline(admin.TabularInline):
    model = models.Recipe.ingredients.through
    min_num = 1


class RecipeAdmin(admin.ModelAdmin):
    exclude = ('is_favorited', 'is_in_shopping_cart')
    list_display = (
        'pk', 'name', 'author', 'cooking_time',
        'text', 'get_tags', 'get_ingredients', 'image')
    list_editable = (
        'name', 'cooking_time', 'text',
        'image', 'author'
    )
    list_filter = ('name', 'author', 'tags')
    empty_value_display = '???'
    inines = [
        RecipeIngredientInline,
        RecipeTagInline,
    ]

    @admin.display(description='Избранное')
    def is_favorited(self, obj):
        return obj.favorite_recipes.count()


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    list_editable = ('user', 'recipe')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    list_editable = ('user', 'recipe')


class TagAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'color', 'slug')
    list_editable = ('name', 'color', 'slug')
    empty_value_display = '???'


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'measurement_unit')
    list_filter = ('name', )
    search_fields = ('name', )


admin.site.register(models.Recipe, RecipeAdmin)
admin.site.register(models.Ingredient, IngredientAdmin)
admin.site.register(models.Tag, TagAdmin)
admin.site.register(models.Favorite, FavoriteAdmin)
admin.site.register(models.ShoppingCart, ShoppingCartAdmin)
admin.site.register(models.IngredientAmount, IngredientAmountAdmin)
admin.site.unregister(Group)
admin.site.unregister(TokenProxy)
