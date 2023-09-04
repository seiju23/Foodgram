from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Кастомный класс юзера."""
    email = models.EmailField(max_length=254, unique=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Класс подписок."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Пользователь')
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='following_restrict'
            )
        ]

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
