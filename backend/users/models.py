from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from foodgram import constants
from api.validators import validate_username


class User(AbstractUser):
    """Кастомный класс юзера."""
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    email = models.EmailField(unique=True)
    username = models.CharField(
        max_length=constants.MAX_LENGTH_USERNAME,
        unique=True,
        validators=[
            UnicodeUsernameValidator(),
            validate_username,
        ]
    )
    first_name = models.CharField(
        max_length=constants.MAX_LENGTH_FIRST_NAME
    )
    last_name = models.CharField(
        max_length=constants.MAX_LENGTH_LAST_NAME
    )
    password = models.CharField(
        verbose_name='Пароль',
        max_length=constants.MAX_LENGTH_PASSWORD,
    )

    class Meta:
        ordering = ['username']
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Класс подписок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subsriber',
        verbose_name='Пользователь')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribing',
        verbose_name='Автор')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='following_restrict'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} подписался на {self.author}'
