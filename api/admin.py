from django.contrib import admin
from .models import Order, OrderItem, User


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
# agregamos el modelo User a los objetos que pueden editarse desde el panel admin
admin.site.register(User)
