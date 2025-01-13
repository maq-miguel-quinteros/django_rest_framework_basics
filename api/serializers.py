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


class OrderSerializer(serializers.ModelSerializer):
    # sobreescribimos order_id para indicar que el mismo sea read_only
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

# heredamos de Serializer en lugar de ModelSerializer
class ProductInfoSerializer(serializers.Serializer):
    products = ProductSerializer(many=True)
    count = serializers.IntegerField()
    max_price = serializers.FloatField()