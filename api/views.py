from django.db.models import Max
from django.shortcuts import get_object_or_404
from api.serializers import ProductSerializer, OrderSerializer, OrderItemSerializer, ProductInfoSerializer
from api.models import Product, Order, OrderItem
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def product_details(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product)
    return Response(serializer.data)


@api_view(['GET'])
def order_list(request):
    # prefetch_related('items'): en su modelo Order tiene un campo products que lo relaciona con el modelo Products
    # está relación se establece mediante el modelo OrderItem que tiene un campo order
    # este campo order tiene se asigna mediante un ForeignKey con un related_name='items'
    # prefetch_related va a hacer la consulta para todas las order que sean un items del modelo OrderItem
    # está forma de traer los datos reduce la cantidad de consultas a la DB al relacionar la orden con los items
    # que (modelo OrderItem) que le corresponden
    orders = Order.objects.prefetch_related('items').all()
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


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