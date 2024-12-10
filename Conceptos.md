## Conventions


* `GET` de muchos elementos: `class` o `def` + `<model_name>_list`, ej. `order_list`. En urls `orders\`
* `GET` de un solo elemento: `class` o `def` + `<model_name>_details`, ej. order_details. en urls `orders\<int:pk>\`

## Models

```py3
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

# class User(AbstractUser): pasamos a controlar el modelo User que tiene por defecto Django
# AbstractUser: heredamos para nuestro modelo User los atributos y métodos
# pass: no modificamos nada de momento en el modelo User
# el modelo cuenta con una propiedad id por defecto
class User(AbstractUser):
    pass

# Product es un modelo = una tabla en la DB
class Product(models.Model):
	# name: propiedad (atributo) de clase = campo (field) de la DB
	# models.CharField(max_length=200) = tipo de campo de longitud máxima en 200
    name = models.CharField(max_length=200)
	#...
    stock = models.PositiveIntegerField()
    # las imágenes se van a guardar en la carpeta products de momento
    image = models.ImageField(upload_to='products/', blank=True, null=True)

	# @property: @ = decorador
	# convierte lo siguiente en una propiedad (atributo) = campo (field) de la DB
    @property
    def in_stock(self):
        return self.stock > 0
    
	# __str__ redefine lo que se muestra con un console log
    def __str__(self):
        return self.name


class Order(models.Model):
    # models.TextChoices: crea opciones pueden ser asignadas a una propiedad (atributo)
	# StatusChoices puede ser cualquier nombre
    class StatusChoices(models.TextChoices):
        PENDING = 'Pending'
        CONFIRMED = 'Confirmed'
        CANCELLED = 'Cancelled'

    # UUID Universal Unique Identify. uuid.uuid4 es método que genera el id
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
	# models.ForeignKey: relaciona el modelo Order con el modelo User mediante su Key (id)
	# a la propiedad user se va a asignar el valor de la propiedad id de un User en particular
	# on_delete=models.CASCADE: al borrar el User borramos todas las Order que tengan en user ese id
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
		# choices: indica cuales son los valores que puede tomar la propiedad
        choices=StatusChoices.choices,
		# default indica el valor por defecto que va a tener la propiedad
        default=StatusChoices.PENDING
    )

	# ManyToManyField: establece la relación entre Order y Product que es de muchos a muchos	
	# products representa los productos de la orden, la propiedad podía llamarse OrderItems u OrderProducts
	# una orden tiene muchos productos y un producto puede aparecer en muchas ordenes
	# through='OrderItem': el modelo OrderItem normaliza la relación entre Order y Product
	# una Order puede tener uno o muchos OrderItem. Un Product puede estar en una o muchas OrderItem
	# una OrderItem solo pertenece a una Order y solo puede tener un Product
    # related_name='orders': lo utilizamos para establecer relaciones mediante un atributo orders en un serializer
    products = models.ManyToManyField(Product, through='OrderItem', related_name='orders')

	# f'': es equivalente a las `` de js
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

## Serializer

Generamos el serializar de forma explicita

```py3
from rest_framework import serializers
from .models import Product

# serializers: permite interpretar, enviar y recibir datos entre DB y front mediante el modelo
# deserializa: datos del front (JSON, XML, otros) -> modelo Product (propiedades)-> DB
# serializa: DB -> modelo Product (propiedades) -> datos al front (JSON, XML, otros)
class ProductSerializer(serializers.Serializer):
    # name = serializers.CharField: propiedad que vamos a serializar y su tipo
    # podemos no serializar todas las propiedades del modelo
    name = serializers.CharField(max_length=200)
    description = serializers.TextField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.PositiveIntegerField()


    # validate_price: función que valida los datos que vienen del front
    # django de forma automática va a correr este método para el atributo price
    # validate_<propiedad>: valida los datos de <propiedad>. Se puede hacer con cualquier propiedadº
    def validate_price(self, value):
        if value < 0:
            # raise es un return para errores
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value
```

Mediante `ModelSerializer` generamos el serializer de forma implícita

```py3
from rest_framework import serializers
from .models import Product, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        # model: modelo que estamos serializando, de aquí toma los tipos de datos para los fields
        model = Product
        # fields: propiedades que vamos a serializar, pueden no ser todas
        fields = (
            # id: es un campo que viene implícito en models.Model, por eso no se declara en el modelo Product
            'id',
            'name',
            'description',
            'price',
            'stock',            
        )

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value
```

## Views & urls

### View function

#### View function

```py3
from django.http import JsonResponse
from api.serializers import ProductSerializer
from api.models import Product

# utilizamos una función para la view
def product_list(request):
    # Product.objects.all(): trae todos los elementos de la DB del modelo Product
    products = Product.objects.all()
    # ProductSerializer(products...): serializa (convierte en JSON) todos los elementos en products.
	# Al products traer mas de un objeto (uno por cada producto) tenemos que indicar many=True
    serializer = ProductSerializer(products, many=True)
    return JsonResponse({
        # devolvemos como JSON los datos serializados
        'data': serializer.data
        })
```

 #### `@api_view` decorator & `Response` object

```py3
from api.serializers import ProductSerializer
from api.models import Product
from rest_framework.response import Response
from rest_framework.decorators import api_view

# @api_view(['GET']): product_list va a ser un 'método view' de tipo api
# (['GET']): solo va a poder recibir métodos HTTP indicados en la lista, en el ejemplo solo de tipo GET
@api_view(['GET'])
def product_list(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    # Response(serializer.data): ordena el tipo de dato que le pasamos (serializer.data) y generar una vista (view)
    return Response(serializer.data)
```

#### Response single object

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

#### Urls

Creamos `urls.py` en la carpeta de la app llamada `api`

```py3
from django.urls import path
from . import views


urlpatterns = [
    path('products/', views.product_list),
    # <int:pk>: el parámetro pk que viene del front es de tipo int
    path('products/<int:pk>/', views.product_details)
]
```

Editamos `urls.py` en la carpeta del proyecto

```py3
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
]
```
