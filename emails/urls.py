from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accounts', views.EmailAccountViewSet)
router.register(r'emails', views.EmailViewSet)

urlpatterns = [
    path('', views.EmailListView.as_view(), name='email_list'),
    path('accounts/', views.AccountListView.as_view(), name='account_list'),
    path('', include(router.urls)),
] 