from django.db import transaction
from rest_framework import serializers
from .models import Product, Order, OrderItem


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

    # podemos crear una función que valide los datos que vienen del front o enviamos
    def validate_price(self, value):
        if value < 0:
            # raise es un return para errores
            raise serializers.ValidationError('El precio tiene que ser mayor que 0')
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    # va a traer los productos que coincidan con la consulta, ya que en el modelo OrderItem tenemos un atributo product que tiene configurada una ForeignKey del modelo Product, es decir, no tenemos que usar el parámetro related_name para este caso 
    # product = ProductSerializer()

    # configuramos de forma explicita los atributos que necesitamos del producto para mostrar
    # product.name: el modelo OrderItem tiene un atributo product que refiere al modelo de Product
    product_name = serializers.CharField(source='product.name')
    product_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        source='product.price')

    class Meta:
        model = OrderItem
        # por defecto solo mostraba el id del producto, ahora que configuramos fuera de meta un atributo product con lo que devuelve el serializer, va a traer esos datos
        fields = ('product_name', 'product_price', 'quantity', 'item_subtotal')

# OrderCreateSerializer: creamos un serializer para manejar el alta de orders
class OrderCreateSerializer(serializers.ModelSerializer):
    # creamos un serializer específico para que quede anidado
    # al funcionar solo en esta clase OrderCreateSerializer no es necesario declararlo afuera
    class OrderItemCreateSerializer(serializers.ModelSerializer):
        class Meta:
            model = OrderItem
            fields = ['product', 'quantity']
    
    # required=False: permite hacer un PUT o POST sin necesidad de tener items en el llamado
    items = OrderItemCreateSerializer(many= True, required=False)
    # sumamos order id para que la respuesta sea igual a la respuesta de la consulta GET
    order_id = serializers.UUIDField(read_only=True)

    # redefinimos el método create del serializer
    # validate_date es lo que nos llega desde la view que utiliza este serializer
    def create(self, validated_data):
        # guardamos en orderitem_data los items que viene en validated_data validated_data
        # pop() guarda en orderitem_data los elementos con clave items y lo elimina de 
        orderitem_data = validated_data.pop('items')

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            for item in orderitem_data:
                OrderItem.objects.create(order=order, **item)
        return order
    
    # instance: son los datos que estamos actualizando, es decir, la orden con sus items
    def update(self, instance, validated_data):
        orderitem_data = validated_data.pop('items')

        # indicamos que todo lo que se realice a continuación sea una transacción
        with transaction.atomic():
            # actualizamos el contenido de la variable instance pasando los datos de la orden sin los items
            instance = super().update(instance, validated_data)

            # Verificamos que tengamos items que actualizar
            if orderitem_data is not None:
                # borramos todos los items que contiene actualmente la orden
                instance.items.all().delete()

            # creamos de nuevo los items con las modificaciones enviadas
            for item in orderitem_data:
                OrderItem.objects.create(order=instance, **item)        
        return instance

    class Meta:
        model = Order
        # los fields que vamos a usar en el alta (order_id', 'created_at' y 'total_price' se crean de forma automática)
        fields = ('order_id','user', 'status', 'items')
        extra_kwargs = {
            'user': {'read_only': True}
        }


class OrderSerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(read_only=True)
    # quitamos el read_only=True de items para poder, mediante un POST, modificar o dar de alta items
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj):
        order_items = obj.items.all()
        return sum(order_item.item_subtotal for order_item in order_items)

    class Meta:
        model = Order
        fields = ('order_id', 'created_at', 'user', 'status', 'items', 'total_price')

# heredamos de Serializer en lugar de ModelSerializer
class ProductInfoSerializer(serializers.Serializer):
    products = ProductSerializer(many=True)
    count = serializers.IntegerField()
    max_price = serializers.FloatField()