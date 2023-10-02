from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'api'

router = DefaultRouter()
router.register(r'recipes', views.RecipeViewSet, basename='recipes')
router.register(r'tags', views.TagViewSet, basename='tags')
router.register(r'users', views.UserViewSet, basename='users')
router.register(
    r'ingredients', views.IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('users/subscriptions/',
         views.FollowListViewSet.as_view({'get': 'list'})),
    path('users/<int:user_id>/subscribe/', views.FollowViewSet.as_view()),
    path('', include(router.urls)),
    path(r'auth/', include('djoser.urls.authtoken')),
]
