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
env/
```

## Create project

Creamos un nuevo proyecto con nombre backend. Puede tener cualquier nombre

```shellscript
django-admin startproject backend .
```
