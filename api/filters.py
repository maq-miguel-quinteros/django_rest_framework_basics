import django_filters
from api.models import Product, Order
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


class OrderFilter(django_filters.FilterSet):
    # sobrescribimos  el atributo created_at
    # DateFilter establece un filtro para el contenido de created_at
    # field_name='created_at__date' extrae del atributo created_at, que es DateTime solo la fecha, Date
    # El formato original es "2024-11-28T21:11:15.606905Z", mediante el filtro queda solo 2024-11-28
    created_at = django_filters.DateFilter(field_name='created_at__date')
    class Meta:
        model = Order
        fields = {
            'status': ['exact'],
            'created_at': ['lt', 'gt', 'exact']
        }