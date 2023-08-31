import os

from django.core.management import BaseCommand
from get_reader import get_reader
from foodgram import settings
from recipes.models import Ingredient


path = os.path.join(settings.BASE_DIR, 'ingredients.csv')


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        reader = get_reader(path)
        next(reader, None)
        for row in reader:
            obj, created = Ingredient.objects.get_or_create(
                id=row[0],
                name=row[1],
                measurement_unit=row[2]
            )
        self.stdout.write(self.style.SUCCESS('Загрузка прошла успешно.'))
