from django.db.models import Max
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.pagination import (LimitOffsetPagination,
                                       PageNumberPagination)
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import InStockFilterBackend, OrderFilter, ProductFilter
from api.models import Order, OrderItem, Product
from api.serializers import (OrderItemSerializer, OrderSerializer,
                             ProductInfoSerializer, ProductSerializer,
                             OrderCreateSerializer)


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


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend]

    # perform_create: indicamos realizar algo cuando create se ejecute
    def perform_create(self, serializer):
        # cuando create se ejecuta ejecutamos save del serializer
        # el user con el que se va a guardar en el serializer va a ser el de la request (logueado)
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        # indicamos el cambio de serializer para create o update
        if self.action == 'create' or self.action == 'update':
            return OrderCreateSerializer
        return super().get_serializer_class()

    # redefinimos el atributo queryset
    def get_queryset(self):
        # traemos todos los datos que devuelve queryset de arriba
        qs = super().get_queryset()
        # si el user que logueado no pertenece al staff, es decir, no es administrador
        if not self.request.user.is_staff:
            # filtramos los elementos para solo devolver los del usuario logueado
            qs = qs.filter(user=self.request.user)
        return qs

    # no necesitamos este endpoint ya que por defecto muestra solo ordenes de usuarios
    # # detail: es True si vamos a mostrar solo un elemento, False para una lista de elementos
    # # url_path: la url a la que responde esta consulta GET
    # @action(
    #     detail=False, 
    #     methods=['get'], 
    #     url_path='user-orders',
    #     # podemos indicar un permiso particular para este action o dejar el que indicamos arriba
    #     # permission_classes=[IsAuthenticated]
    #     )
    # def user_orders(self, request):
    #     # trae lo que tiene el atributo queryset mas arriba
    #     # da a user en el filtro el valor del usuario de la request (usuario logueado)
    #     orders = self.get_queryset().filter(user=request.user)
    #     serializer = self.get_serializer(orders, many=True)
    #     return Response(serializer.data)


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