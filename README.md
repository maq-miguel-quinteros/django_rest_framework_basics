[Django REST Framework series](https://www.youtube.com/watch?v=6AEvlNgRPNc&list=PL-2EBeDYMIbTLulc9FSoAXhbmXpLq2l5t&index=1)

# Fundamentos

Vamos a generar una base de datos que cuente con las siguiente tablas:
* `Product`: para datos de productos
* `OrderItem`: tabla intermedia entre `Product` y `Order`
* `Order`: ordenes de compras de productos
* `User`: quien genera una nueva orden de compra
* Otras clases para establecer permisos de usuarios

# Setup and Models

## Setup

### Virtual environment

```shellscript
python -m venv env
env/Scripts/activate # source env/bin/activate in GitHub Codespaces
```

### Dependencies

Creamos un archivo `requirements.txt` con el siguiente contenido

```plaintext
asgiref==3.8.1
Django==5.1.1
django-extensions==3.2.3
djangorestframework==3.15.2
pillow==10.4.0
sqlparse==0.5.1
tzdata==2024.2
```

Instalamos las dependencias

```shellscript
pip install -r requirements.txt
# o
pip install -r backend/requirements.txt # if pull project
```

### Git ignore

Creamos un archivo `.gitignore` con el siguiente contenido

```plaintext
*.pyc
__pycache__
db.sqlite3
.env
```

### Create project

Creamos un nuevo proyecto con nombre backend. Puede tener cualquier nombre

```shellscript
django-admin startproject backend .
```

### Create api app

Creamos una nueva app llamada `api`

```shellscript
python manage.py startapp api
```

En `backend` configuramos `settings.py`

```py3
INSTALLED_APPS = [
	#...
	# agregamos las apps
    'rest_framework',
    'api'
]
```

## Models

### Models

En `models.py` de `api`

```py3
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

# creamos un modelo de usuario en base al modelo AbstractUser
class User(AbstractUser):
    pass


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    # las imágenes de los productos se van a guardar en una carpeta de medios y dentro en la carpeta products
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    # property genera una columna en la base de datos, que se va a llamar in_stock, que va a ser True or False, en base a una función que generamos con def
    @property
    def in_stock(self):
        return self.stock > 0
    
    def __str__(self):
        return self.name


class Order(models.Model):
    # TextChoices permite crear opciones que puede tomar alguna columna de la base de datos
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending'
        CONFIRMED = 'Confirmed'
        CANCELLED = 'Cancelled'

    # UUID Universal Unique Identify. uuid.uuid4 es la función que genera el id
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )

    # el campo products va a contener los productos de la orden estableciendo una relación de muchos a muchos con el modelos Product, esta relación se va a establecer mediante el modelo OrderItem (through='OrderItem')
    products = models.ManyToManyField(Product, through='OrderItem', related_name='orders')

    def __srt__(self):
        return f'Order {self.order_id} by {self.user.username}'
    

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    @property
    def item_subtotal(self):
        return self.product.price * self.quantity
    
    def __str__(self):
        return f'{self.quantity} x {self.product.name} in order {self.order.order_id}'
```

En `backend` configuramos `settings.py`. Agregamos al final del archivo

```py3
# Como configuramos un modelo de usuario personalizado tenemos que declarar el mismo
AUTH_USER_MODEL = 'api.User'
```

### Makemigrations & migrate

```shellscript
python manage.py makemigrations
python manage.py migrate
```

## Data for testing

En `api` creamos la carpeta `management` y dentro la carpeta `commands`. En commands creamos el archivo `__init__.py`, que queda vacío, este sirve para indicar que al ejecutar la aplicación debe ejecutarse el contenido de la carpeta donde se aloja, y creamos el archivo `populate_db.py` al que cargamos lo siguiente. Mediante este archivo vamos a crear datos de prueba en la base de datos que creamos antes con migrate

```py3
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import lorem_ipsum
from api.models import User, Product, Order, OrderItem

class Command(BaseCommand):
    help = 'Creates application data'

    def handle(self, *args, **kwargs):
        # get or create superuser
        user = User.objects.filter(username='admin').first()
        if not user:
            user = User.objects.create_superuser(username='admin', password='test')

        # create products - name, desc, price, stock, image
        products = [
            Product(name="A Scanner Darkly", description=lorem_ipsum.paragraph(), price=Decimal('12.99'), stock=4),
            Product(name="Coffee Machine", description=lorem_ipsum.paragraph(), price=Decimal('70.99'), stock=6),
            Product(name="Velvet Underground & Nico", description=lorem_ipsum.paragraph(), price=Decimal('15.99'), stock=11),
            Product(name="Enter the Wu-Tang (36 Chambers)", description=lorem_ipsum.paragraph(), price=Decimal('17.99'), stock=2),
            Product(name="Digital Camera", description=lorem_ipsum.paragraph(), price=Decimal('350.99'), stock=4),
            Product(name="Watch", description=lorem_ipsum.paragraph(), price=Decimal('500.05'), stock=0),
        ]

        # create products & re-fetch from DB
        Product.objects.bulk_create(products)
        products = Product.objects.all()


        # create some dummy orders tied to the superuser
        for _ in range(3):
            # create an Order with 2 order items
            order = Order.objects.create(user=user)
            for product in random.sample(list(products), 2):
                OrderItem.objects.create(
                    order=order, product=product, quantity=random.randint(1,3)
                )
```

Creamos los datos de prueba en la base de datos

```shellscript
python manage.py populate_db
```

# Serializers & Response objects | Browsable API

## ModelSerializer for Product

En `api` creamos el archivo `serializers.py`. Mediante los serializers podemos convertir los modelos de datos de Django (que son las tablas de la DB) en JSON o XML, para poder enviarlos al front. A su vez los serializers validan y convierten los datos en JSON o XML que llegan desde el front en datos que podemos utilizar mediante los modelos (deserialize)

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        # para saber el tipo de dato de cada elemento de fields se basa en el model, es decir, para name el tipo de datos es models.CharField
        fields = (
            # es un campo que viene implícito en models.Model, por eso no se declara en el modelo Product
            'id',
            'name',
            'description',
            'price',
            'stock',            
        )

    # podemos crear una función que valide los datos que vienen del front o enviamos
    def validate_price(self, value):
        if value <= 0:
            # raise es un return para errores
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value
```

## View function for Product

```py3
from django.http import JsonResponse
from api.serializers import ProductSerializer
from api.models import Product

# una función que vamos usar como view, la cual va a devolver una lista de productos
def product_list(request):
    # traemos todos los productos de la db usando el modelo Product
    products = Product.objects.all()
    # indicamos que tiene que serializar (convertir en json) para devolver, todos los elementos que traemos en products. Al products traer mas de un objeto (uno por cada producto) tenemos que indicar many=True
    serializer = ProductSerializer(products, many=True)
    return JsonResponse({
        'data': serializer.data
        })
```

## Urls for Product

En `api` creamos el archivo `urls.py`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.product_list)
]
```

En `backend` editamos el archivo `urls.py`

```py3
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
]
```

## Api view with response object

```py3
# from django.http import JsonResponse
from api.serializers import ProductSerializer
from api.models import Product
from rest_framework.response import Response
from rest_framework.decorators import api_view

# mediante @api_view definimos que product_list va a ser un 'método view' de tipo api, indicamos que solo va a poder recibir métodos HTTP de tipo GET
@api_view(['GET'])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    # la clase Response se encarga, mediante el serializer que pasamos, de ordenar el tipo de dato de la respuesta y generar una vista (view)
    return Response(serializer.data)
```

## Response a single object

En `api` editamos `views.py`

```py3
from django.shortcuts import get_object_or_404
from api.serializers import ProductSerializer
from api.models import Product
from rest_framework.response import Response
from rest_framework.decorators import api_view


@api_view(['GET'])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
# pk: id que pasamos como parámetro en el navegador
def product_details(request, pk):
    # get_object_or_404: devuelve error 404 de forma automática si no encuentra el Product con id=pk
    product = get_object_or_404(Product, pk=pk)
    # serializa solo un objeto Product
    serializer = ProductSerializer(product)
    return Response(serializer.data)
```

En `api` editamos `urls.py`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.product_list),
    # mediante <int:pk> indicamos que es un valor int que se va a identificar como pk en la request que viene del front
    path('products/<int:pk>/', views.product_details)
]
```

# Nested Serializers, SerializerMethodField and Serializer Relations

## Nested serializer

### Model & serializer

En `api` editamos `models.py`

```py3
#...

class OrderItem(models.Model):
    order = models.ForeignKey(
            Order, 
            on_delete=models.CASCADE,
            # related_name: indica como puede llamarse este campo desde un serializer
            related_name='items'
        )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

#...
```

Configuramos el serializer para el modelo `Order`. Este tiene un atributo `products` que está relacionado con el modelo `OrderItem`. Configuramos el serializer anidado para este par de modelos. En `api` editamos `serializers.py`

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem

#...

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('product', 'quantity')

# OrderSerializer, en su field items, va a mostrar instancias de OrderItemSerializer
class OrderSerializer(serializers.ModelSerializer):
    # anidamos el OrderItemSerializer dentro de OrderSerializer.
    # Traemos los registros del modelo OrderItem de su atributo order
    # Para establecer la coincidencia el nombre del atributo items tiene que coincidir con el related_name='items' del modelo OrderItem.
    # Ya que el modelo desde donde traemos los datos es Order, en OrderItem configuramos la ForeignKey Order
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        # agregamos a los fields propios del modelo el field items que creamos arriba
        fields = ('order_id', 'created_at', 'user', 'status', 'items')
```

### Views & urls

En `api` editamos `views.py`

```py3
from django.shortcuts import get_object_or_404
from api.serializers import ProductSerializer, OrderSerializer, OrderItemSerializer
from api.models import Product, Order, OrderItem
from rest_framework.response import Response
from rest_framework.decorators import api_view

#...

@api_view(['GET'])
def order_list(request):
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)
```

En `api` editamos `urls.py`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.product_list),    
    path('products/<int:pk>/', views.product_details),
    path('orders/', views.order_list),
]
```

## SerializerMethodField

En `api` editamos `serializers.py`

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem

#...

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    # creamos un atributo que vamos a asignar con lo que devuelva el método que pasamos mediante SerializerMethodField.
    # Podemos pasar el método entre los () o 
    # podemos llamar al método get_NOMBRE_MÉTODO y django va a interpretar que este el el método que asignará valores al atributo
    total_price = serializers.SerializerMethodField()

    # definimos la función que va a utilizar SerializerMethodField para dar valor a total_price
    def get_total_price(self, obj):
        # obj es la consulta que estamos realizando en ese momento mediante el serializer
        # en este caso obj es el modelo Order. El modelo Order tiene un atributo con related_name = items
        order_items = obj.items.all()
        # subtotal es un atributo que generamos en el modelo OrderItem
        return sum(order_item.item_subtotal for order_item in order_items)

    class Meta:
        model = Order
        # agregamos a los fields propios del modelo el field items que creamos arriba
        fields = ('order_id', 'created_at', 'user', 'status', 'items', 'total_price')
```

## Nested Serializer without related_name

En `api` editamos `serializer.py`

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem

#...

class OrderItemSerializer(serializers.ModelSerializer):
    # va a traer los productos que coincidan con la consulta
    # en el modelo OrderItem tenemos un atributo product que tiene configurada una ForeignKey del modelo Product
    # no tenemos que usar el parámetro related_name para este caso 
    product = ProductSerializer()
    class Meta:
        model = OrderItem
        # por defecto solo mostraba el id del producto
        # configuramos fuera de meta un atributo product con lo que devuelve el serializer
        fields = ('product', 'quantity')

#...
```

## Adding model properties to serializer

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem

#...

class OrderItemSerializer(serializers.ModelSerializer):
    # configuramos de forma explicita los atributos que necesitamos del producto para mostrar
    # product.name: el modelo OrderItem tiene un atributo product que refiere al modelo de Product
    product_name = serializers.CharField(source='product.name')
    product_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        source='product.price')

    class Meta:
        model = OrderItem
        fields = ('product_name ', 'product_price', 'quantity', 'item_subtotal')

#...
```

* `PrimaryKeyRelatedField`: permite mostrar el id del modelo de la relación
* `StringRelatedField`: permite mostrar en la respuesta del serializer lo que devuelve el método `__str__`.
* `HyperlinkedRelatedField`: permite establecer un link a una vista para los objetos de la relación

# Serializer subclasses and Aggregated API data

Editamos `serializers.py` en `api`

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem

#...

# heredamos de Serializer en lugar de ModelSerializer
class ProductInfoSerializer(serializers.Serializer):
    products = ProductSerializer(many=True)
    count = serializers.IntegerField()
    max_price = serializers.FloatField()
```

Editamos `views.py` en `api`

```py3
from django.db.models import Max

#...

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

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.product_list),
    path('products/info/', views.product_info),
    path('products/<int:pk>/', views.product_details),
    path('orders/', views.order_list),
]
```

# django-silk for Profiling and Optimization with Django REST Framework


## Install `django-silk`

Instalamos el paquete `django-silk` que vamos a utilizar para analizar los query que mandamos a la API. Este complemento nos muestra todos los llamados que hacemos a la API y cuantas consultas a la DB hace ese llamado. Esto nos permite optimizar las consultas a la DB, editando las views para que la query sea mas precisa y requiera menos consultas a la DB

```shellscript
pip install django-silk
```

Editamos `settings.py` en `backend`

```py3
#...

INSTALLED_APPS = [
    #...
    'rest_framework',
    'api',
    'silk' ,
]

MIDDLEWARE = [
    #...
    'seda.middleware.SilkyMiddleware',
]

#...
```

Editamos `urls.py` en `backend`

```py3
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
    path('silk/', include('silk.urls', namespace='silk')),
]
```

## Profiling (análisis de rendimiento de software)

Mediante el complemento `django-silk` observamos que la vista `/orders/` realiza más de 10 consultas a la DB. Editamos `views.py` en `api` para corregir eso

```py3
#...

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

#...
```

Mejoramos más las consultas

```py3
#...

@api_view(['GET'])
def order_list(request):
    # ('items__product'): vamos a traer, de los items, los productos que estén relacionados a la orden
    # El modelo Order tiene instancias del modelo Product en su atributo products mediante el modelo OrderItem
    # El modelo OrderItem relaciona Order y Product mediante sus ForeignKey
    # En el caso del atributo order del modelo OrderItem indicamos que el related_name='items'
    # Al llamar a items__product indicamos que para cada order id de sus items devuelva lor products relacionados
    # all() no es necesario después de prefetch_related
    orders = Order.objects.prefetch_related('items__product')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

#...
```

# Generic Views | ListAPIView & RetrieveAPIView

Mediante las vistas genéricas podemos crear vistas asignando valores a atributos de clases que sobre escribimos. Estas vistas genéricas se encargan de hacer el CRUD hacia la base de datos. 

## ListAPIView (GET)

Editamos `views.py` en `api`

```py3
#...

from rest_framework import generics

# generics.ListAPIView: heredamos de la clase ListAPIView, preparada para devolver un listado elementos de la DB
class ProductListAPIView(generics.ListAPIView):
    # queryset: la búsqueda que va a realizar en la DB
    queryset = Product.objects.all()
    # serializer_class: el serializer que va a utilizar la vista
    serializer_class = ProductSerializer


class OrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.product_info),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
]
```

## RetrieveAPIView (GET)

Editamos `views.py` en `api`

```py3
#...

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

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.product_info),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
]
```

## Changing base queryset

```py3
#...

class ProductListAPIView(generics.ListAPIView):
    # stock__gt=0: indicamos que filtre los elementos del modelo Product que tengan el atributo stock mayor a 0
    queryset = Product.objects.filter(stock__gt=0)
    serializer_class = ProductSerializer

#...
```

# Dynamic Filtering | Overriding get_queryset() method

Si queremos que una consulta esté ligada al usuario autenticado en ese momento necesitamos sobre escribir el `queryset`. Esto lo hacemos mediante el método `get_queryset`. Tenemos que sobrescribir esté atributo por que, mediante el atributo `queryset` no tenemos acceso al request de la llamada. Para poder generar un filtro dinámico de los objetos que vamos a mostrar necesitamos acceder a los datos de la llamada que vienen en el request.

## Registering models with admin and creating Inline

Registramos el modelo en el administrador de django para poder generar elementos desde ahí. Creamos el superuser mediante el comando



```shellscript
python manage.py createsuperuser
```

Editamos `admin.py` en `api`.

```py3
from django.contrib import admin
from models import Order, OrderItem


# TabularInline: permite adjuntar objetos relacionados a otros objetos cuando los creamos de forma dinámica
class OrderItemInline(admin.TabularInline):
    model = OrderItem

# OrderAdmin: mediante esta clase vamos a integrar los modelos de Order y OrderItem al admin de django
class OrderAdmin(admin.ModelAdmin):
    # inlines: indicamos, o en este caso sumamos, columnas al modelo Order, lo que sumamos es OrderItem
    inlines = [
        OrderItemInline
    ]

# admin.site.register: registra en el sitio de admin el modelo Order mediante la clase OrderAdmin
admin.site.register(Order, OrderAdmin)
```

## Dynamically filtering queryset with get_queryset() method

Editamos `views.py` en `api`

```py3
#...

# UserOrderListAPIView: ordenes de un usuario específico
class UserOrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer

    def get_queryset(self):
        # super().get_queryset(): traemos el contenido del atributo queryset de arriba
        qs = super().get_queryset()
        # filter(user=self.request.user): filtramos qs pasando como parámetro de filtro el usuario logueado
        # user=self.request.user: mediante self podemos acceder al request y de ahí al user de ese request
        return qs.filter(user=self.request.user)

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.product_info),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
    path('user-orders/', views.UserOrderListAPIView.as_view()),
]
```

# Permissions and Testing Permissions

Configuramos django para que, en ciertas vistas, solo usuarios autenticados puedan ver los datos que corresponden a ese usuario

## Permissions 

Editamos `views.py` en `api`

```py3
#...

from rest_framework.permissions import IsAuthenticated

#...

class UserOrderListAPIView(generics.ListAPIView):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    # permission_classes: permite establecer los permisos para consultar la view
    # IsAuthenticated: solo permite realizar la consulta a usuarios autenticados
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()        
        return qs.filter(user=self.request.user)
    
#...
```

##  Testing API permissions with Django TestCase

Vamos a generar un test mediante TestCase de django. Mediante este test vamos a verificar el funcionamiento de la vista restringida para usuarios autenticados.

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.product_info),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
    # agregamos un mane al path de las ordenes de usuarios autenticados
    path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]
```

En el primer test creamos un usuario, hacemos login mediante `force_login`, llamamos a la api mediante `get(reverse('user-orders'))` para el usuario logueado y mediante `order['user'] == user.id` verificamos que todas las orders que devuelve la api sean del usuario logueado.

En el segundo teste llamaos a la api mediante `get(reverse('user-orders'))`, la cual, al no estar autenticados, nos va a devolver `403`, mediante `assertEqual(response.status_code, 403)` chequeamos que esa sea la respuesta, validando el test ya que el mismo da el error que esperamos para usuarios no autenticados.

Editamos `test.py` en `api`

```py3
from django.test import TestCase
from .models import Order, User
# reverse la utilizamos para hacer llamados a las path de las urls desde el test
from django.urls import reverse
from rest_framework import status

# TestCase: clase desde la cual vamos a configurar el test
class UserOrderTestClass(TestCase):
    # setUp: configuramos las variables que van a generarse en el test para poder realizarlo
    def setUp(self):
        user1 = User.object.create_user(username='user1', password='test')
        user2 = User.object.create_user(username='user2', password='test')
        Order.object.create(user=user1, total_amount='44.44')
        Order.object.create(user=user1, total_amount='66.44')
        Order.object.create(user=user2, total_amount='22.44')
        Order.object.create(user=user2, total_amount='11.44')
    
    # definimos lo que va a hacer el test
    def test_user_order_endpoint_retrieves_only_authenticated_user_orders(self):
        # traemos los datos del usuario en user
        user = User.objects.get(username='user1')
        # client.force_login: en clases que heredan de TestCase tenemos el objeto client
        # client tiene métodos como force_login que permiten tratar de hacer login con el user que le pasamos
        self.client.force_login(user)
        # hacemos un llamado a la api en el path con name user-orders y la respuesta se guarda en response
        response = self.client.get(reverse('user-orders'))
        # si response.status_code == 200 da false muestra el error y termina la ejecución
        # si da true sigue con la siguiente línea
        assert response.status_code == status.HTTP_200_OK
        orders = response.json()
        # self.assertTrue: para que pasé el assert debe devolver true
        # all: todo lo que se evalúe en all tiene que ser true
        # order['user'] == user.id: para order compara el valor de user por el valor de id del user de arriba
        self.assertTrue(all(order['user'] == user.id for order in orders))

    def test_user_order_list_unauthenticated(self):
        response = self.client.get(reverse('user-orders'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

Para correr el test ejecutamos

```shellscript
python manage.py test
```

# APIView class

Mediante `APIView` podemos definir funciones que pueden encargarse de los métodos `GET`, `POST`, `PUT`, y demás con una lógica interna propia que no depende de la lógica predefinida en las `APIView` de `generics`.

Editamos `views.py` en `api`

```py3
#...

from rest_framework.views import APIView

#...

# def get(): definimos el método get para métodos HTTP GET
class ProductInfoAPIView(APIView):
    def get(self, request):
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
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.ProductInfoAPIView.as_view()),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
    path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]
```

# Creating Data | ListCreateAPIView and Generic View Internals

## Creating data with CreateAPIView (POST)

Podemos utilizar el serializer ya creado para una llamada GET con el field `id` y generar un nuevo serializer para la llamada POST con el field `description` (que necesitamos para crear un nuevo elemento). En lugar de eso vamos a modificar el serializer para no generar uno nuevo.

Editamos `serializers.py` en `api`

```py3
#...

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            # quitamos el field id y agregamos description
            # esta modificación también cambia lo que devuelven los endpoint get
            'description',
            'name',
            'description',
            'price',
            'stock',            
        )
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value

#...
```

Editamos `views.py` en `api`

```py3
#...

class ProductListAPIView(generics.ListAPIView):
    # volvemos a traer todos los objetos a esta vista
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    

# generics.CreateAPIView: heredamos de la clase CreateAPIView, preparada para crear un elemento en la DB
class ProductCreateAPIView(generics.CreateAPIView):
    # model: el modelo de base para crear el nuevo elemento
    model = Product
    # editamos el serializer ProductSerializer para que tenga entre sus fields description
    # description es necesario para poder dar de alta un elemento
    serializer_class = ProductSerializer

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/create/', views.ProductCreateAPIView.as_view()),
    path('products/info/', views.ProductInfoAPIView.as_view()),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
    path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]
```

## ListCreateAPIView (GET, POST)

Utilizamos la misma ruta para crear una instancia (POST) y para listar las instancias (GET). Podemos consultar el funcionamiento de estas clases y sus atributos en la web [cdrf.co](https://www.cdrf.co/)

Editamos `views.py` en `api`

```py3
#...

# class ProductListAPIView(generics.ListAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer

# ListCreateAPIView: la clase que hereda de ListCreateAPIView va a poder manejar
# llamadas POST para crear una nueva instancia
# llamadas GET para listar las instancias
class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # es posible editar los métodos list y create que se heredan de ListCreateAPIView
    # se pueden crear listas personalizadas o altas de objetos personalizados editando estos


# class ProductCreateAPIView(generics.CreateAPIView):
#     model = Product
#     serializer_class = ProductSerializer

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListCreateAPIView.as_view()),
    # path('products/create/', views.ProductCreateAPIView.as_view()),
    path('products/info/', views.ProductInfoAPIView.as_view()),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),
    path('orders/', views.OrderListAPIView.as_view()),
    path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]
```

# Customizing permissions in Generic Views | VSCode REST Client extension

## VSCode REST Client extension

Editamos los permisos de la clase ProductListCreateAPIView para que cualquier usuario pueda hacer un llamado GET y listar todos los productos, pero que solo usuarios autenticados puedan hacer un llamado POST para crear un nuevo producto.

Para probar los permisos instalamos la extensión de VSCode `rest client`.

Creamos el archivo `api.http` en la carpeta base del proyecto

```http
# La solicitud muestra un JSON con todos los productos
GET http://localhost:8000/products/ HTTP/1.1

###

# La solicitud da de alta un producto
POST http://localhost:8000/products/ HTTP/1.1
Content-Type: application/json

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}
```

## Customizing permissions in Generic Views

Al enviar cualquiera de las dos consultas la respuesta es correcta. Necesitamos restringir la consulta POST para que solo usuarios admin puedan dar de alta productos.

Editamos `views.py` en `api`

```py3
#...
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny


class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # get_permissions: permite modificar el atributo permission_classes de forma dinámica
    def get_permissions(self):
        # AllowAny: permisos para cualquier usuario
        self.permission_classes = [AllowAny]
        # request.method == 'POST': si el método es POST modificamos permission_classes
        if self.request.method == 'POST':
            self.permission_classes = [IsAdminUser]
        return super().get_permissions()

#...
```

Cuando volvemos a correr las peticiones HTTP

```http
# La solicitud muestra un JSON con todos los productos
GET http://localhost:8000/products/ HTTP/1.1

###

# La solicitud muestra el error "detail": "Authentication credentials were not provided."
# No estamos logueados como admin para poder hacer el alta
POST http://localhost:8000/products/ HTTP/1.1
Content-Type: application/json

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}
```

# JWT Authentication with djangorestframework

## Setting authentication scheme

Configuramos como vamos a trabajar la autenticación en el proyecto configurando la misma en las settings

Editamos `settings.py` en la carpeta principal del proyecto

```py3
#...

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
		# autenticación de las llamadas HTTP
        'rest_framework.authentication.BasicAuthentication',
		# autenticación basada en sesiones
		# Es la que usa Django por defecto para trabajar con el panel admin
        'rest_framework.authentication.SessionAuthentication',
    ]
}
```

### djangorestframework-simplejwt

Podemos realizar la autenticación mediante token, lo que requiere una consulta a la Base de datos. La autenticación mediante JWT (JSON Web Token authentication) no requiere una consulta a la base de datos. Para realizar esto instalamos la librería `djangorestframework-simplejwt`.

```shellscript
pip install djangorestframework-simplejwt
```

Editamos settings.py en la carpeta principal del proyecto para agregar `simplejwt`

```py3
#...

# Agregamos la configuración de autenticación de rest_frameworks
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        #'rest_framework.authentication.BasicAuthentication',
        # Quitamos BasicAuthentication para trabajar en su lugar con JWTAuthentication
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}
```

Tenemos que agregar las rutas de login para este método de autenticación.

Editamos `urls.py` en la carpeta principal del proyecto

```py3
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
    path('silk/', include('silk.urls', namespace='silk')),
    # rutas para obtener el token de autenticación y para hacer el refresh del mismo
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

Probamos el login mediante simplejwt mediante una llamada al path que configuramos

Editamos `api.http` en la carpeta base del proyecto

```http
#...

# Hacemos login en la aplicación
POST http://localhost:8000/api/token/ HTTP/1.1
Content-Type: application/json

{
    "username": "admin",
    "password": "test"
}

###
# con el access token que devuelve el llamado anterior damos de alta el producto que antes deba error
# Esta vez no devuelve error. El token tiene los datos del usuario admin en su encriptado
# El usuario admin tiene los permisos para crear productos en el path products mediante POST
POST http://localhost:8000/products/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2Mjg4OTQyLCJpYXQiOjE3MzYyODg2NDIsImp0aSI6IjQzOGMzOTdhMTlkNDQ0NDFiOGI3MDQwNDBkNTFjZGJiIiwidXNlcl9pZCI6MX0.NFUbNu02pgF6twrAtG-c8ntbEpSkaspOY8uzlKmOKvA

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}
```

Editamos el usuario de pruebas para que no tenga permisos de admin, de esta manera podemos probar si usuarios que no tengan esos permisos pueden crear nuevos registros.

Editamos `admin.py` en `api`

```py3
from django.contrib import admin
from .models import Order, OrderItem, User

#...
admin.site.register(Order, OrderAdmin)
# agregamos el modelo User a los objetos que pueden editarse desde el panel admin
admin.site.register(User)
```

El el panel admin aparece ahora el modelo User. Dentro podemos ver que tenemos 2 user, el admin y el que creamos (maq). Editamos el user maq para que no sea un usuario administrador quitando el tilde a la opción `Staff status`. El usuario maq ya no va a poder iniciar sesión en el panel admin.

Al realizar el login y luego tratar de hacer el alta de un producto con el token del usuario maq dará un error. Para probar editamos `api.http` en la carpeta base del proyecto

```http
#...

POST http://localhost:8000/api/token/ HTTP/1.1
Content-Type: application/json

{
    "username": "maq",
    "password": "4123"
}

###
# dará el error: You do not have permission to perform this action.
POST http://localhost:8000/products/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}

###
# También necesitamos pasar el token para la consulta que muestra las ordenes creadas por el usuario
GET http://localhost:8000/user-orders/ HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A
```

## Corregimos los test

Al estar utilizando la autenticación mediante JWT el tipo de respuesta de error de los test que creamos cambia.

Editamos `tests.py` en `api`

```py3
#...

class UserOrderTestClass(TestCase):
    def setUp(self):
        user1 = User.objects.create_user(username='user1', password='test')
        user2 = User.objects.create_user(username='user2', password='test')
        Order.objects.create(user=user1)
        Order.objects.create(user=user1)
        Order.objects.create(user=user2)
        Order.objects.create(user=user2)    

    def test_user_order_endpoint_retrieves_only_authenticated_user_orders(self):
        user = User.objects.get(username='user1')
        self.client.force_login(user)
        response = self.client.get(reverse('user-orders'))
        assert response.status_code == status.HTTP_200_OK
        orders = response.json()
        self.assertTrue(all(order['user'] == user.id for order in orders))

    def test_user_order_list_unauthenticated(self):
        response = self.client.get(reverse('user-orders'))
        # Cambiamos 403 por 401 ya que la autenticación por JWT que estamos usando devuelve ese error
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
```

# Refresh Tokens & JWT Authentication

El access token tiene un tiempo de vida. Una vez que ese tiempo se termina ese token deja de ser válido. Si necesitamos generar un nuevo access token sin tener que volver a hacer login utilizamos el refresh token.

Editamos `api.http` en la carpeta base del proyecto

```http
#...

# Enviamos el refresh token como parte del body de la consulta
POST http://localhost:8000/api/token/refresh/ HTTP/1.1
Content-Type: application/json

{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A"
}
```

# Updating & Deleting data

Podemos agrupar todas las acciones que hacen referencia a un solo elemento de la base de datos, estos son, ver el elemento, actualizar el elemento o eliminar el elemento, en un único path de la forma `/products/<int:id>/`. Para esto utilizamos la generic view `RetrieveUpdateDestroyAPIView`. Según el tipo de llamada HTTP que enviemos, GET para consulta, PUT o PATCH para actualizar y DELETE para borrar, la view va a modificar la base de datos. Esto sirve para una única instancia del modelo.

Editamos `views.py` en `api`

```py3
#...

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

#...
```

Editamos `api.http` en la carpeta base del proyecto

```http
# Probamos la consulta, modificación y borrado de elementos

# Consulta de un elemento
GET http://localhost:8000/api/products/1/ HTTP/1.1

###

# Actualización de elemento
PUT http://localhost:8000/api/products/1/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}

###
PATCH http://localhost:8000/api/products/1/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A

{
    "name": "Television",
    "price": 300.00,
    "stock": 14,
    "description": "An amazing new TV"
}

###

# Borrado del elemento
DELETE  http://localhost:8000/api/products/1/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM2MjkyMzQ4LCJpYXQiOjE3MzYyOTIwNDgsImp0aSI6IjlhMjM2NzcxNDY4MDQ3NmZiZTExNzgzOGVmMWU4Y2RjIiwidXNlcl9pZCI6Mn0.5xMJOoRPKdt7fMOnjCXYA1bKtoNdmBGB8cEr6BE0y3A
```

# Django REST Framework API Documentation

Para hacer la documentación de forma automática de la API instalamos drf-spectacular (drf: Django Rest Framework).

```shellscript
pip install drf-spectacular
```

Editamos `settings.py` en la carpeta principal del proyecto

```py3
#...

INSTALLED_APPS = [
	#...
    'silk',
	# agregamos la app
    'drf_spectacular',
]

#...

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
	# indicamos el esquema como default
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Agregamos la configuración particular de drf_spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Product API',
    'DESCRIPTION': 'Your project description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
}
```

Generamos el esquema mediante el siguiente comando

```shellscript
python manage.py spectacular --color --file schema.yml
```

Agregamos las rutas donde vamos a poder visualizar la documentación. Si accedemos a la ruta `'api/schema/'` solo descarga el schema. Si accedemos a la ruta `'api/schema/swagger-ui/'` vamos a poder visualizar la documentación de la api que se genera de forma automática con esta librería.

Editamos `urls.py` de la carpeta principal del proyecto

```py3
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
    path('silk/', include('silk.urls', namespace='silk')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # agregamos las rutas propias de drf_spectacular
    # YOUR PATTERNS
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

# django-filter and DRF API filtering

Podemos realizar consultas y, a los datos que devolvemos desde la base de datos al front, aplicar un filtro que viene dispuesto desde el front por el usuario.

## Creating django-filter Filter Backend [link](https://www.django-rest-framework.org/api-guide/filtering/#djangofilterbackend)

Instalamos djangoFilterBackend con el siguiente comando

```shellscript
pip install django-filter
```

Editamos `settings.py` en la carpeta principal del proyecto

```py3
#...

INSTALLED_APPS = [
	#...
    'drf_spectacular',
	# agregamos la app de django_filters
    'django_filters',
]

#...

REST_FRAMEWORK = {
	#...
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
	# Configuramos django_filters como el paquete de filtro por defecto
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

#...
```

Tenemos que indicar a las vistas cuales son los fields que van a aceptar filtros.

Editamos `views.py` en `api`

```py3
#...

class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # indicamos que se van a poder realizar filtros sobre los atributos name y price
    filterset_fields = ('name', 'price')

#...
```

Para realizar el filtro basta con indicar `api/products/?name=Television`. La consulta nos va a devolver los elementos que, en el atributo name, tengan Television.

Este tipo de filtro solo sirve para búsquedas que igualen el resultado. Es decir, si queremos buscar por el atributo price, pero que sea mayor o menor a 300, no podemos realizar esa búsqueda.

Tampoco podemos buscar por palabras aproximadas. Si buscamos por television en minúsculas no va a traer el producto.

## Defining FilterSet class for more flexible filtering

Para definir filtros mas flexibles creamos un archivo de filtros. Desde la documentación [link](https://django-filter.readthedocs.io/en/latest/guide/usage.html) configuramos el archivo.

Creamos `filters.py` en `api`

```py3
import django_filters
from api.models import Product


class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            # exact: el name tiene que indicar exacto lo que pasamos como filtro
            # iexact:  igual que el anterior solo que ignora mayúsculas y minúsculas
            # contains: el name contiene algo de lo indicado en el filtro
            # icontains: igual que el anterior ignorando mayúsculas y minúsculas            
            'name': ['iexact', 'icontains'],
            # lt': menor que, 'gt': mayor que, 'range': en el rango
            'price': ['exact', 'lt', 'gt', 'range']
        }
```

Editamos `views.py` en `api`

```py3
#...
from api.filters import ProductFilter

#...

class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # filterset_fields = ('name', 'price')
    # agregamos la clase ProductFilter para el atributo filterset_class de la view
    filterset_class = ProductFilter

#...
```

Para consultar, por ejemplo, un precio mayor que, a la llamada la hacemos como `products/?price__gt=100` (dos guiones bajos). Para range hacemos la llamada como `products/?price__range=10.50`, la llamada se hace para el rango entre 10 y 50. Para name podemos indicar `products/?name__icontains=tele`.

# SearchFilter and OrderingFilter

## SearchFilter

Para agregar filtros de búsqueda desde el backend lo hacemos mediante un paquete que viene instalado en rest framework

Editamos `views.py` en `api`

```py3
#...

# importamos las librerías que permiten aplicar filtros desde el backend
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend


class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    # indicamos a la view mediante que librerías se van a realizar filtros
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    # indicamos cuales son los fields con los que vamos a realizar la búsqueda filtrada
    # la búsqueda se realiza por ambos fields a la vez
    # =name: las búsquedas que hagamos tiene que coincidir exacto con el valor de name
    search_fields = ['=name', 'description']

#...
```

Para realizar una búsqueda mediante un filtro utilizamos `/products/?search=vision`. Las búsquedas no son sensibles a mayúsculas o minúsculas.

## OrderingFilter

Lo utilizamos para devolver los datos solicitados por el front con un orden en particular desde el back

Editamos `views.py` en `api`

```py3
#...

class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter,
        # agregamos la clase que vamos a utilizar para realizar el ordenamiento
        filters.OrderingFilter
        ]
    search_fields = ['name', 'description']
    # indicamos los fields sobre los cuales podemos ordenar los datos devueltos
    #
    ordering_fields = ['name', 'price', 'stock']

#...
```

Para realizar una búsqueda mediante un filtro utilizamos `products/?ordering=price`. Si queremos el orden inverso podemos utilizar el - (menos) en el parámetro de ordenamiento `products/?ordering=-price`

Para aplicar ambos filtros lo hacemos mediante un & de la forma `products/?ordering=-price&search=lorem`


# Writing Filter Backends

Definimos un filtro propio desde el backend

Editamos `filters.py` en `api`

```py3
#... 

from rest_framework import filters

# creamos un filtro para devolver solo productos en stock
class InStockFilterBackend(filters.BaseFilterBackend):
    # editamos el filter_queryset con nuestro filtro
    def filter_queryset(self, request, queryset, view):
        # indicamos que, del queryset filtre, para los elementos stock, solo los mayores que 0
        return queryset.filter(stock__gt=0)

#... 
```

Editamos `views.py` en `api`

```py3
#...
# importamos el filtro personalizado
from api.filters import ProductFilter, InStockFilterBackend
#...

class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # filterset_fields = ('name', 'price')
    filterset_class = ProductFilter
    filter_backends = [
        #...
        # agregamos el filtro personalizado
        InStockFilterBackend
        ]

#...
```

Al agregar el filtro personalizado, de forma automática se van a filtrar los productos con stock 0, es decir, estos no van a aparecer para cualquier búsqueda que hagamos.

# PageNumberPagination y LimitOffsetPagination

Podemos realizar la paginación de los resultados de un llamada a la API desde el back, de esta forma ir entregando por partes los resultados del llamado.

## PageNumberPagination

Editamos settings.py en la carpeta principal del proyecto

```py3
#...
REST_FRAMEWORK = {
	#...
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    # configuramos la clase por defecto para hacer la paginación
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # cantidad de resultados que va a mostrar por página
    'PAGE_SIZE': 5,
}
```

Al llamar a `/products/` vemos que en la respuesta ya contamos con un atributo next donde tenemos la url `/products/?page=2`. Si ingresamos en esta URL vamos a ver los elementos restantes de la búsqueda.

Podemos aplicar filtros como `products/?ordering=-price`, para el atributo next vamos a ver que la url indica 
`products/ordering=-price&page=2`

podemos configurar la paginación solo para una view en particular

Editamos `views.py` en `api`

```py3
#...
from rest_framework.pagination import PageNumberPagination


class ProductListCreateAPIView(generics.ListCreateAPIView):
    # para evitar errores en el servidor cuando se realiza la paginación
    # hace un primer orden de los elementos que trae mediante pk
    queryset = Product.objects.order_by('pk')
    serializer_class = ProductSerializer
    # configuramos la clase con la que vamos a hacer la paginación
    pagination_class = PageNumberPagination
    # configuramos la cantidad de elementos por página
    pagination_class.page_size = 3
    # podemos editar el nombre del atributo en el navegador que va a representar las páginas
    # la paginación se verá como /products/?pagenum=2
    pagination_class.page_query_param = 'pagenum'
    # podemos permitir al front que nos indique la cantidad de elementos por página
    # la paginación se verá como /products/?pagenum=2&size=2
    pagination_class.page_size_query_param = 'size'
    # para evitar que el usuario seleccione cantidades de elementos grandes como 1000
    pagination_class.max_page_size = 5
#...
```

## LimitOffsetPagination

Podemos configura la clase LimitOffsetPagination para la paginación de forma predeterminada en settings.py, como hicimos con PageNumberPagination o para una view en particular.

Editamos `views.py` en `api`

```py3
#...
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination


class ProductListCreateAPIView(generics.ListCreateAPIView):
    queryset = Product.objects.order_by('pk')
    serializer_class = ProductSerializer
    # indicamos la clase por defecto para la paginación
    pagination_class = LimitOffsetPagination
    # también podemos cambiar el nombre del atributo limit y establecer un máximo para el límite
    pagination_class.limit_query_param = 'number'
    pagination_class.max_limit = 5

#...
```

En la URL del llamado ahora podemos indicar un `limit` y un `offset` de la forma `products/?limit=2&offset=3`, donde limit es la cantidad de elementos que va a devolver en la página y offset es el número del elemento desde donde va a mostrar. En el ejemplo vamos a devolver 2 elementos pero en esta página vamos a mostrar desde el elemento 3.

# [ViewSets](https://www.django-rest-framework.org/api-guide/viewsets/) and [Ruters](https://www.django-rest-framework.org/api-guide/routers/)

Mediante las ViewSets podemos agrupar bajo una misma view distintos tipos de métodos HTTP (GET, POST, PUT...) a métodos Python llamados actions.

Editamos `views.py` en `api`

```py3
#...

from rest_framework import viewsets

#...

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    # podemos deshabilitar la paginación por defecto (que indicamos en settings.py)
    pagination_class = None


# class OrderListAPIView(generics.ListAPIView):
#     queryset = Order.objects.prefetch_related('items__product')
#     serializer_class = OrderSerializer

# class UserOrderListAPIView(generics.ListAPIView):
#     queryset = Order.objects.prefetch_related('items__product')
#     serializer_class = OrderSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         qs = super().get_queryset()
#         return qs.filter(user=self.request.user)

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter


urlpatterns = [
    path('products/', views.ProductListCreateAPIView.as_view()),
    # path('products/create/', views.ProductCreateAPIView.as_view()),
    path('products/info/', views.ProductInfoAPIView.as_view()),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),    
    # path('orders/', views.OrderListAPIView.as_view()),
    # path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]

# creamos una variable que hereda los métodos de DefaultRouter
router = DefaultRouter()
# registramos un path en el objeto con la view a la que va a apuntar
router.register('orders/', views.OrderViewSet)
# sumamos el path creado al listado de paths de la variable urlpatterns
# se crean path como orders/ y orders/<int:pk>
# según el método HTTP los pedidos se van a manejar desde las actions
urlpatterns += router.urls
```

Cuando vamos a crear una nueva orden, con un llamado POST, necesitamos que el id de la orden se cree de forma automática, es decir, que nosotros no podamos crear ese atributo desde el formulario de alta de ordenes.

Editamos `serializers.py` en `api`

```py3
#...

class OrderSerializer(serializers.ModelSerializer):
    # sobrescribimos order_id para indicar que el mismo sea read_only
    # mediante esto order_id no va a aparecer en el formulario de alta de orden
    order_id = serializers.UUIDField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        order_items = obj.items.all()
        return sum(order_item.item_subtotal for order_item in order_items)

    class Meta:
        model = Order
        fields = ('order_id', 'created_at', 'user', 'status', 'items', 'total_price')

#...
```

# Viewset Action, filtering and permission  

Instalamos `isort` para ordenar las importaciones en `views.py`

```shellscript
pip install isort
isort .\api\views.py
```

## Filtering

Editamos `filters.py` en `api`

```py3
#...

from api.models import Product, Order

#...

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
    
#...
```

Editamos `views.py` en `api`

```py3
#...

from api.filters import InStockFilterBackend, OrderFilter, ProductFilter

#...

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend]

#...
```

Podemos utilizar los filtros como antes, mediante el path `orders/?status=Pending`, así como también `orders/?created_at__gt=2024-09-30`. En el caso de la fecha debe estar en el formato `yyyy-mm-dd`. 

## Actions and permission

Para poder mantener la view que nos devolvía las ordenes según el usuario (`user-orders/`), utilizando para la misma la lógica que venimos usando en la viewset OrderViewSet, nos vemos en la necesidad de generar nuevas action, además de las que ya vienen por defecto con la ViewSet como ser create o retrieve. Seguimos lo indicado en el [link](https://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing)

Editamos `views.py` en `api`

```py3
# ...

from rest_framework.decorators import api_view, action

#...

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend]

    # detail: es True si vamos a mostrar solo un elemento, False para una lista de elementos
    # url_path: la url a la que responde esta consulta GET
    @action(
        detail=False, 
        methods=['get'], 
        url_path='user-orders',
        # podemos indicar un permiso particular para este action o dejar el que indicamos arriba
        # permission_classes=[IsAuthenticated]
        )
    def user_orders(self, request):
        # trae lo que tiene el atributo queryset mas arriba
        # da a user en el filtro el valor del usuario de la request (usuario logueado)
        orders = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)

#... 
```

# Viewset Permissions | Admin vs. Normal User

Modificamos la clase OrderViewSet para que los usuarios normales puedan ver, editar y borrar sus propias ordenes y solo los usuarios administradores puedan ver, editar y borrar las ordenes de todos los usuarios

Editamos `views.py` en `api`

```py3
#...

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('items__product')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend]

    # redefinimos el atributo queryset
    def get_queryset(self):
        # traemos todos los datos que devuelve queryset de arriba
        qs = super().get_queryset()
        # si el user que logueado no pertenece al staff, es decir, no es administrador
        if not self.request.user.is_staff:
            # filtramos los elementos para solo devolver los del usuario logueado
            qs = qs.filter(user=self.request.user)
        return qs
    
    # no necesitamos este endpoint ya que por defecto muestra solo ordenes del usuario logueado
    # @action(
    #     detail=False, 
    #     methods=['get'], 
    #     url_path='user-orders',
    #     )
    # def user_orders(self, request):
    #     orders = self.get_queryset().filter(user=request.user)
    #     serializer = self.get_serializer(orders, many=True)
    #     return Response(serializer.data)

#...
```

Hacemos el usuario que creamos antes (maq) como usuario común

Editamos `api.http` en la carpeta base del proyecto

```http
###
# hacemos login del usuario y pegamos el access token para poder hacer la consulta
GET  http://localhost:8000/api/orders/
Authorization: Bearer <<INGRESAR ACCESS TOKEN>>
```
