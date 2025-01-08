import django_filters
from api.models import Product


class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            # 'contains': el name contiene algo de lo indicado en el filtro
            'name': ['exact', 'icontains'],
            # lt': menor que, 'gt': mayor que, 'range': en el rango
            'price': ['exact', 'lt', 'gt', 'range']
        }