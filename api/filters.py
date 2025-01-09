import django_filters
from api.models import Product
from rest_framework import filters

# creamos un filtro para devolver solo productos en stock
class InStockFilterBackend(filters.BaseFilterBackend):
    # editamos el filter_queryset con nuestro filtro
    def filter_queryset(self, request, queryset, view):
        # indicamos que, del queryset filtre, para los elementos stock, solo los mayores que 0
        return queryset.filter(stock__gt=0)

class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            # 'contains': el name contiene algo de lo indicado en el filtro
            'name': ['exact', 'icontains'],
            # lt': menor que, 'gt': mayor que, 'range': en el rango
            'price': ['exact', 'lt', 'gt', 'range']
        }