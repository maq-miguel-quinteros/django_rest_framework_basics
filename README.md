[Django REST Framework series](https://www.youtube.com/watch?v=6AEvlNgRPNc&list=PL-2EBeDYMIbTLulc9FSoAXhbmXpLq2l5t&index=1)

# Fundamentos

Vamos a generar una base de datos que cuente con las siguiente tablas:
* `Product`: para datos de productos
* `OrderItem`: tabla intermedia entre `Product` y `Order`
* `Order`: ordenes de compras de productos
* `User`: quien genera una nueva orden de compra
* Otras clases para establecer permisos de usuarios

# Setup

## Virtual environment

```shellscript
python -m venv env
env/Scripts/activate # source env/bin/activate in GitHub Codespaces
```

## Dependencies

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

## Git ignore

Creamos un archivo `.gitignore` con el siguiente contenido

```plaintext
*.pyc
__pycache__
db.sqlite3
.env
```

## Create project

Creamos un nuevo proyecto con nombre backend. Puede tener cualquier nombre

```shellscript
django-admin startproject backend .
```

## Create api app

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

# Models

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

## Makemigrations & migrate

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
