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

#...
```

Editamos `urls.py` en `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.ProductListAPIView.as_view()),
    path('products/info/', views.product_info),
    path('products/<int:pk>/', views.product_details),
    path('orders/', views.order_list),
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

# Dynamic Filtering | Overriding get_queryset() method
