from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin
)
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from recipes.models import (
    Recipe, Ingredient, Favorite,
    ShoppingCart, Tag, IngredientAmount)
from .serializers import (
    UserSerializer, FavoriteSerializer, ShoppingCartSerializer,
    SetPasswordSerializer, IngredientSerializer, TagSerializer,
    RecipeReadSerializer, RecipeWriteSerializer,
    FollowSerializer)
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
    serializer_class = UserSerializer
    pagination_class = PageNumberPagination
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
        permission_classes=[IsAuthenticated],
        serializer_class=UserSerializer
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

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,),
            pagination_class=PageNumberPagination)
    def subscriptions(self, request):
        queryset = User.objects.filter(subscribing__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def subscribe(self, request, **kwargs):
        author = get_object_or_404(User, id=kwargs['pk'])

        if request.method == 'POST':
            serializer = FollowSerializer(
                author, data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(user=request.user, author=author)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            get_object_or_404(
                Follow, user=request.user,
                author=author).delete()
            return Response(
                {'detail': 'Вы отписались от автора.'},
                status=status.HTTP_204_NO_CONTENT)


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
    pagination_class = PageNumberPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    http_method_names = ['get', 'post', 'patch', 'delete']

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
            serializer = FavoriteSerializer(
                recipe, data=request.data,
                context={"request": request})
            serializer.is_valid(raise_exception=True)
            if not Favorite.objects.filter(
                user=request.user,
                    recipe=recipe).exists():
                Favorite.objects.create(user=request.user, recipe=recipe)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return Response(
                {'errors': 'Рецепт уже в избранном.'},
                status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            get_object_or_404(
                Favorite, user=request.user,
                recipe=recipe).delete()
            return Response(
                {'detail': 'Вы удалили рецепт из избранного.'},
                status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,),
            pagination_class=None)
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            serializer = ShoppingCartSerializer(
                recipe, data=request.data,
                context={"request": request})
            serializer.is_valid(raise_exception=True)
            if not ShoppingCart.objects.filter(
                user=request.user,
                    recipe=recipe).exists():
                ShoppingCart.objects.create(user=request.user, recipe=recipe)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED)
            return Response(
                {'errors': 'Вы уже добавили этот рецепт.'},
                status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'DELETE':
            get_object_or_404(
                ShoppingCart, user=request.user,
                recipe=recipe).delete()
            return Response(
                {'detail': 'Вы удалили рецепт из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_shopping_cart(request):
    recipes = request.user.shopping_cart.all().values('recipe_id')
    ingredients = IngredientAmount.objects.filter(recipe__in=recipes)

    if not ingredients:
        return Response(
            {'errors': 'Список покупок не может быть пустым.'},
            status=status.HTTP_204_NO_CONTENT)

    shopping_list = ingredients.values(
        'ingredient__name', 'ingredient__measurement_unit').order_by(
        'ingredient__name').annotate(amount=Sum('amount'))

    file = HttpResponse(
        'Cписок покупок:\n' + '\n'.join(shopping_list),
        content_type='text/plain')
    file['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
    return file
