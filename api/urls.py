from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter


urlpatterns = [
    path('products/', views.ProductListCreateAPIView.as_view()),
    # path('products/create/', views.ProductCreateAPIView.as_view()),
    path('products/info/', views.ProductInfoAPIView.as_view()),
    path('products/<int:product_id>/', views.ProductDetailAPIView.as_view()),    
    # path('orders/', views.OrderListAPIView.as_view()),
    # path('user-orders/', views.UserOrderListAPIView.as_view(), name='user-orders'),
]

# creamos una variable que hereda los métodos de DefaultRouter
router = DefaultRouter()
# registramos un path en el objeto con la view a la que va a apuntar
router.register('orders', views.OrderViewSet)
# sumamos el path creado al listado de paths de la variable urlpatterns
urlpatterns += router.urls