from rest_framework.pagination import PageNumberPagination


class LimitPaginator(PageNumberPagination):
    page_size_query_param = 'limit'
