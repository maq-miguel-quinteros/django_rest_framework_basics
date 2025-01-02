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