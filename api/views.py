from django.db.models import Max
from django.shortcuts import get_object_or_404
from api.serializers import ProductSerializer, OrderSerializer, OrderItemSerializer, ProductInfoSerializer
from api.models import Product, Order, OrderItem
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import generics

# generics.ListAPIView: heredamos de la clase ListAPIView, preparada para devolver un listado elementos de la DB
class ProductListAPIView(generics.ListAPIView):
    # queryset: la búsqueda que va a realizar en la DB
    queryset = Product.objects.all()
    # serializer_class: el serializer que va a utilizar la vista
    serializer_class = ProductSerializer

# generics.RetrieveAPIView: heredamos de la clase RetrieveAPIView
# por defecto va a tomar el parámetro pk que viene en la llamada /products/<int:pk>
# y va a devolver esa instancia buscando en Product.objects.all()
class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # podemos sobre escribir los atributos
    # lookup_field: si no se sobre escribe es pk. La clase va a generar la búsqueda a partir de este atributo
    # lookup_url_kwarg: el valor en la url que hace la consulta, por defecto es pk.
    lookup_url_kwarg = 'product_id'


class OrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer


@api_view(['GET'])
def product_info(request):
    products = Product.objects.all()
    # pasamos al serializer genérico ProductInfoSerializer los datos con los que debe generar su respuesta
    serializer = ProductInfoSerializer({
        # mediante products indicamos crear el serializer anidado 
        'products': products,
        # len cuenta la cantidad de objetos product que trae el query Product.objects.all()
        'count': len(products),
        # aggregate: agrega el campo que componemos dentro del paréntesis a los objetos en products
        # max_price=Max('price'): Max devuelve el valor máximo de la columna price de la DB y lo asigna a max_price
        # ['max_price']: el nombre que va a tener el campo que agregamos, no tiene que coincidir con max_price=Max...
        'max_price': products.aggregate(max_price=Max('price'))['max_price']
    })
    return Response(serializer.data)