from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .utils import create_object_util, delete_object_util
from .filters import RecipeFilter
from .pagination import MyPaginator
from .permissions import IsAuthorOrReadOnly
from recipes.models import (
    Recipe, Ingredient, Favorite,
    ShoppingCart, Tag, IngredientAmount)
from .serializers import (
    UserSerializer, FavoriteSerializer, ShoppingCartSerializer,
    SetPasswordSerializer, IngredientSerializer, TagSerializer,
    RecipeReadSerializer, RecipeWriteSerializer, UserReadSerializer,
    FollowSerializer, FollowListSerializer)
from users.models import User, Follow


class UserViewSet(CreateModelMixin,
                  ListModelMixin,
                  RetrieveModelMixin,
                  viewsets.GenericViewSet):
    """Получение пользователей."""
    queryset = User.objects.all()
    filter_backends = (SearchFilter,)
    search_fields = ('username',)
    permission_classes = (AllowAny,)
    pagination_class = MyPaginator
    serializer_class = UserSerializer
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        if request.method == 'PUT':
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        else:
            return super().update(request, *args, **kwargs)

    @action(
        methods=['get', 'patch', ],
        detail=False,
        url_path='me',
        permission_classes=(IsAuthenticated,),
        serializer_class=UserReadSerializer
    )
    def my_profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(role=user.role)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['post'],
            permission_classes=(IsAuthenticated,))
    def set_password(self, request):
        serializer = SetPasswordSerializer(request.user, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(
            {'detail': 'Вы изменили пароль.'},
            status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, pk):
        if request.method == 'POST':
            author = get_object_or_404(User, id=pk)
            serializer = FollowSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if request.user.is_authenticated:
                author = get_object_or_404(User, id=pk)
                if not Follow.objects.filter(
                    user=request.user, author=author
                ).exists():
                    return Response(
                        {'errors': 'Вы не подписаны на этого пользователя'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                Follow.objects.get(
                    user=request.user.id,
                    author=pk).delete()
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


class IngredientViewSet(ListModelMixin,
                        RetrieveModelMixin,
                        viewsets.GenericViewSet):
    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (SearchFilter,)
    search_fields = ('^name', )


class TagViewSet(ListModelMixin,
                 RetrieveModelMixin,
                 viewsets.GenericViewSet):
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
    pagination_class = MyPaginator

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'retrieve':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return create_object_util(request, recipe, FavoriteSerializer)

        if request.method == 'DELETE':
            if Favorite.objects.filter(user=request.user,
                                       recipe=recipe).exists():
                error_message = 'Этого рецепта нет в избранном.'
                return delete_object_util(
                    request, Favorite,
                    recipe, error_message)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return create_object_util(
                request, recipe,
                ShoppingCartSerializer)

        if request.method == 'DELETE':
            if ShoppingCart.objects.filter(user=request.user,
                                           recipe=recipe).exists():
                error_message = 'Этого рецепта нет в списке покупок'
                return delete_object_util(
                    request, ShoppingCart,
                    recipe, error_message)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False,
            methods=['get'],
            permission_classes=(IsAuthenticated,)
            )
    def download_shopping_cart(self, request):
        if not request.user.shopping_cart.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        ingredients = IngredientAmount.objects.filter(
            recipe__shopping_recipe__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        if not ingredients:
            return Response(
                {'errors': 'Список покупок не может быть пустым.'},
                status=status.HTTP_204_NO_CONTENT)

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
