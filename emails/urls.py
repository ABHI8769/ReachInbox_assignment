from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accounts', views.EmailAccountViewSet)
router.register(r'emails', views.EmailViewSet)

urlpatterns = [
    # Template views (frontend)
    path('app/emails/', views.EmailListView.as_view(), name='email_list'),
    path('app/accounts/', views.AccountListView.as_view(), name='account_list'),
    
    # API endpoints
    path('api/', include(router.urls)),
] 