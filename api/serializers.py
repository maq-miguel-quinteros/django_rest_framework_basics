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
        if value < 0:
            # raise es un return para errores
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('product', 'quantity')


class OrderSerializer(serializers.ModelSerializer):
    # anidamos el OrderItemSerializer dentro de OrderSerializer. Traemos los registros del modelo OrderItem. Para establecer la coincidencia el nombre del atributo items tiene que coincidir con el related_name='items' del modelo OrderItem. Ya que el modelo desde donde traemos los datos es Order, en OrderItem configuramos la ForeignKey Order
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        # agregamos a los fields propios del modelo el field items que creamos arriba
        fields = ('order_id', 'created_at', 'user', 'status', 'items')
