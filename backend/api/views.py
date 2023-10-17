from django.contrib.auth import get_user_model
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser import views

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,)
from rest_framework.response import Response

from .filters import RecipeFilter
from .pagination import LimitPaginator
from .permissions import IsAuthorOrReadOnly
from recipes.models import (
    Recipe, Ingredient, Favorite,
    ShoppingCart, Tag, IngredientAmount)
from .serializers import (
    FavoriteSerializer, ShoppingCartSerializer,
    IngredientSerializer, TagSerializer,
    RecipeReadSerializer, RecipeWriteSerializer,
    FollowSerializer, FollowListSerializer)
from users.models import Follow


User = get_user_model()


class UserViewSet(views.UserViewSet):
    """Получение пользователей."""
    queryset = User.objects.all()
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    pagination_class = LimitPaginator
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        if request.method == 'POST':
            author = get_object_or_404(User, id=id)
            serializer = FollowSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            author = get_object_or_404(User, id=id)
            delete_nums, _ = Follow.objects.filter(
                user=request.user, author=author
            ).delete()
            if not delete_nums:
                return Response(
                    {'errors': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=self.request.user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowListSerializer(
            pages,
            many=True,
            context={'request': request})
        return self.get_paginated_response(serializer.data)

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = [IsAuthenticated, ]
        return super(UserViewSet, self).get_permissions()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (SearchFilter,)
    search_fields = ('^name', )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (AllowAny, )
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для рецептов."""
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = LimitPaginator

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def create_object_util(request, instance, serializer_name):
        """Функция для создания объекта избранного или списка покупок."""
        serializer = serializer_name(
            data={'user': request.user.id, 'recipe': instance.id, },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            return self.create_object_util(
                request, recipe,
                FavoriteSerializer)
        if request.method == 'DELETE':
            try:
                favorite = Favorite.objects.filter(
                    user=request.user, recipe=recipe)
            except Recipe.DoesNotExist:
                raise NotFound(
                    {'error': 'Рецепт не существует.'}
                )
            if not favorite.exists():
                return Response(
                    {'error': 'Рецепта нет в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            return self.create_object_util(
                request, recipe,
                ShoppingCartSerializer)
        if request.method == 'DELETE':
            try:
                shopping_cart = ShoppingCart.objects.filter(
                    user=request.user, recipe=recipe)
            except Recipe.DoesNotExist:
                raise NotFound(
                    {'error': 'Рецепт не существует.'}
                )
            if not shopping_cart.exists():
                return Response(
                    {'error': 'Рецепта нет в списке покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @staticmethod
    def create_txt_file(ingredients, request):
        shopping_list = (
            f'Список покупок для: {request.user.username}\n\n'
        )
        shopping_list += '\n'.join([
            f'- {ingredient["ingredient__name"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            f' - {ingredient["amount"]}'
            for ingredient in ingredients
        ])
        filename = f'{request.user.username}_shopping_list.txt'
        file = HttpResponse(
            shopping_list,
            content_type='text/plain')
        file['Content-Disposition'] = f'attachment; filename={filename}'
        return file

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated,)
            )
    def download_shopping_cart(self, request):
        if not request.user.shoppings_cart.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        ingredients = IngredientAmount.objects.filter(
            recipe__shoppings_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        if not ingredients:
            return Response(
                {'errors': 'Список покупок не может быть пустым.'},
                status=status.HTTP_204_NO_CONTENT)
        return self.create_txt_file(ingredients, request)
