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
    # va a traer los productos que coincidan con la consulta, ya que en el modelo OrderItem tenemos un atributo product que tiene configurada una ForeignKey del modelo Product, es decir, no tenemos que usar el parámetro related_name para este caso 
    product = ProductSerializer()
    class Meta:
        model = OrderItem
        # por defecto solo mostraba el id del producto, ahora que configuramos fuera de meta un atributo product con lo que devuelve el serializer, va a traer esos datos
        fields = ('product', 'quantity')


class OrderSerializer(serializers.ModelSerializer):
    # anidamos el OrderItemSerializer dentro de OrderSerializer. Traemos los registros del modelo OrderItem. Para establecer la coincidencia el nombre del atributo items tiene que coincidir con el related_name='items' del modelo OrderItem. Ya que el modelo desde donde traemos los datos es Order, en OrderItem configuramos la ForeignKey Order
    items = OrderItemSerializer(many=True, read_only=True)

    # creamos un atributo que vamos a asignar con lo que devuelva el método que pasamos como mediante SerializerMethodField. Podemos pasar el método entre los () o podemos llamar al método get_NOMBRE_MÉTODO y django va a interpretar que este el el método que asignará valores al atributo
    total_price = serializers.SerializerMethodField()

    # definimos la función que va a utilizar SerializerMethodField para dar valor a total_price
    def get_total_price(self, obj):
        # obj es la consulta que estamos realizando en ese momento mediante el serializer
        order_items = obj.items.all()
        # subtotal es un atributo que generamos en el modelo OrderItem
        return sum(order_item.item_subtotal for order_item in order_items)

    class Meta:
        model = Order
        # agregamos a los fields propios del modelo el field items que creamos arriba
        fields = ('order_id', 'created_at', 'user', 'status', 'items', 'total_price')
