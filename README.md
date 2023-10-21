# Foodgram

### Описание
Фудграм - это проект онлайн-сервиса и API для продуктового помощника. Он включает в себя:
- Создание и редактирование рецептов
- Подписки на авторов
- Добавление интересных рецептов в избранное
- Автоматическое формирование и скачивание в виде текстового файла списка покупок - ингредиентов, необходимых для приготовления выбранных рецептов

Проект доступен по адресу https://seiju23project.sytes.net

Полная документация к API находится в файле [docs/openapi-schema.yml](docs/openapi-schema.yml) и доступна по эндпоинту `/api/docs/`.

### Используемые технологии
- Python 3.11
- Django
- Django REST Framework
- PostgreSQL
- Gunicorn
- Nginx
- Docker
- GitHub Actions

### Как развернуть проект локально
1. Клонировать репозиторий:
    ```bash
    git clone git@github.com:seiju23/foodgram-project-react.git
    cd foodgram-project-react/infra/
    ```
2. Создать .env файл со следующими параметрами:
    ```bash
    DEBUG=True
    DB_PROD=False
    ```
3. Запустить сервер Django и наполнить БД ингредиентами:
    ```bash
    python manage.py runserver
    python manage.py load_csv
    ```

#### Запуск через Docker Compose
1. Создать в папке infra/ файл `.env` с переменными окружения.
2. Собрать и запустить докер-контейнеры через Docker Compose:
    ```bash
    docker compose up --build
    ```

### Об авторе
Игорь Равлис (github:[@seiju23](github.com/seiju23), tg:[@seiju23](t.me/seiju23))
