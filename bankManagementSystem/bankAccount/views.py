from django.db import transaction
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from core.models import BankAccount
from .serializers import BankAccountSerializer


class BankAccountViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """A ViewSet for managing Bank Accounts: Create, Suspend, Activate, and Close only."""

    serializer_class = BankAccountSerializer
    queryset = BankAccount.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Limit the queryset to the authenticated user's accounts."""
        return self.queryset.filter(user=self.request.user)

    @action(methods=['PATCH'], detail=True, url_path='suspend')
    def suspend(self, request, pk=None):
        """Suspend a bank account"""
        bank_account = self.get_object()

        if bank_account.status == 'closed':
            return Response({'detail': 'Cannot suspend a closed account.'}, status=status.HTTP_400_BAD_REQUEST)
        if bank_account.status == 'suspended':
            return Response({'detail': 'Account is already suspended.'}, status=status.HTTP_400_BAD_REQUEST)

        bank_account.status = 'suspended'
        bank_account.save()
        return Response(self.get_serializer(bank_account).data, status=status.HTTP_200_OK)

    @action(methods=['PATCH'], detail=True, url_path='activate')
    def activate(self, request, pk=None):
        """Activate a suspended bank account"""
        bank_account = self.get_object()

        if bank_account.status == 'closed':
            return Response({'detail': 'Cannot activate a closed account.'}, status=status.HTTP_400_BAD_REQUEST)
        if bank_account.status == 'active':
            return Response({'detail': 'Account is already active.'}, status=status.HTTP_400_BAD_REQUEST)
        if bank_account.status != 'suspended':
            return Response({'detail': 'Only suspended accounts can be activated.'}, status=status.HTTP_400_BAD_REQUEST)

        bank_account.status = 'active'
        bank_account.save()
        return Response(self.get_serializer(bank_account).data, status=status.HTTP_200_OK)

    @action(methods=['DELETE'], detail=True, url_path='close')
    @transaction.atomic
    def close(self, request, pk=None):
        """Close a bank account"""
        bank_account = self.get_object()

        if bank_account.status == 'closed':
            return Response({'detail': 'Account is already closed.'}, status=status.HTTP_400_BAD_REQUEST)

        if bank_account.balance < 0:
            return Response({'detail': 'Account cannot be closed with a negative balance.'},
                            status=status.HTTP_400_BAD_REQUEST)

        bank_account.delete()
        return Response({'detail': 'Account successfully closed and deleted.'}, status=status.HTTP_204_NO_CONTENT)
