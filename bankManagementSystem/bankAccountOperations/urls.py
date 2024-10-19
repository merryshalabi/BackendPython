from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bankAccountOperations.views import BankAccountViewSet, LoanViewSet

# Create a router and register the BankAccountViewSet and LoanViewSet
router = DefaultRouter()
router.register('bankaccounts', BankAccountViewSet, basename='bankaccounts')
router.register('loans', LoanViewSet, basename='loans')

app_name = 'bankAccountOperations'

# Include the router URLs
urlpatterns = [
    path('', include(router.urls)),
]
