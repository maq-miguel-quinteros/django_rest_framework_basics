from django.db.models import Max
from django.shortcuts import get_object_or_404
from api.serializers import ProductSerializer, OrderSerializer, OrderItemSerializer, ProductInfoSerializer
from api.models import Product, Order, OrderItem
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.views import APIView
from api.filters import ProductFilter, InStockFilterBackend
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination


class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.order_by('pk')
    serializer_class = ProductSerializer
    pagination_class = LimitOffsetPagination
    pagination_class.limit_query_param = 'number'
    pagination_class.max_limit = 5

    # pagination_class.page_size = 3
    # pagination_class.page_size_query_param = 'size'
    # pagination_class.max_page_size = 5
    # filterset_fields = ('name', 'price')
    filterset_class = ProductFilter
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter,
        filters.OrderingFilter,
        InStockFilterBackend
        ]
    # =name: las búsquedas que hagamos tiene que coincidir exacto con el valor de name
    search_fields = ['=name', 'description']
    # indicamos los fields sobre los cuales podemos ordenar los datos devueltos
    ordering_fields = ['name', 'price', 'stock']

    # get_permissions: permite modificar el atributo permission_classes de forma dinámica
    def get_permissions(self):
        # AllowAny: permisos para cualquier usuario
        self.permission_classes = [AllowAny]
        # request.method == 'POST': si el método es POST modificamos permission_classes
        if self.request.method == 'POST':
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()


# Podemos actualizar el nombre de la clase para dejarlo con la convención ProductRetrieveUpdateDestroyAPIView
class ProductDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_url_kwarg = 'product_id'

    # agregamos el mismo tipo de autenticación que utilizamos para el alta de productos
    def get_permissions(self):
        self.permission_classes = [AllowAny]
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()



class OrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer

# UserOrderListAPIView: ordenes de un usuario específico
class UserOrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    # permission_classes: permite establecer los permisos para consultar la view
    # IsAuthenticated: solo permite realizar la consulta a usuarios autenticados
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # super().get_queryset(): traemos el contenido del atributo queryset de arriba
        qs = super().get_queryset()
        # filter(user=self.request.user): filtramos qs pasando como parámetro de filtro el usuario logueado
        # user=self.request.user: mediante self podemos acceder al request y de ahí al user de ese request
        return qs.filter(user=self.request.user)


# def get(): definimos el método get para métodos HTTP GET
class ProductInfoAPIView(APIView):
    def get(self, request):
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