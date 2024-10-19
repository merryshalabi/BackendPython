from decimal import Decimal
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import BankAccount, Loan
from .serializers import DepositSerializer, WithdrawalSerializer, BalanceSerializer, TransferSerializer, LoanSerializer


class BankAccountViewSet(viewsets.GenericViewSet):
    """
    A ViewSet for managing bank account operations.
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = BankAccount.objects.all()

    def get_queryset(self):
        """Retrieve bank accounts for the authenticated user"""
        account_id = self.request.query_params.get('account_id')
        queryset = self.queryset.filter(user=self.request.user)

        if account_id:
            queryset = queryset.filter(id=account_id)

        return queryset

    def get_serializer_class(self):
        """Returns the appropriate serializer class based on the action"""
        if self.action == 'deposit':
            return DepositSerializer
        elif self.action == 'withdraw':
            return WithdrawalSerializer
        elif self.action == 'balance':
            return BalanceSerializer
        elif self.action == 'transfer':
            return TransferSerializer
        return None

    @action(methods=['POST'], detail=False, url_path='deposit')
    def deposit(self, request):
        """Handle deposit to a bank account"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Deposit successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False, url_path='withdraw')
    def withdraw(self, request):
        """Handle withdrawal from a bank account"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Withdrawal successful"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='account_id',
                description='ID of the bank account to retrieve balance for',
                required=True,
                type=OpenApiTypes.INT
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        }
    )
    @action(methods=['GET'], detail=False, url_path='balance')
    def balance(self, request):
        """Retrieve balance of a bank account"""
        account_id = request.query_params.get('account_id')
        if not account_id:
            return Response({"account_id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account = BankAccount.objects.get(pk=account_id, user=request.user)
        except BankAccount.DoesNotExist:
            return Response({"detail": "Account not found or does not belong to you."},
                            status=status.HTTP_404_NOT_FOUND)

        if account.status in ['suspended', 'closed']:
            return Response({"detail": "Cannot retrieve balance for a suspended or closed account."},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({"balance": account.balance}, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='transfer')
    def transfer(self, request):
        """Transfer funds between accounts"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            transfer_data = serializer.save()
            return Response({
                "message": "Transfer successful",
                "source_account": transfer_data['source_account'],
                "target_account": transfer_data['target_account']
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoanViewSet(viewsets.GenericViewSet):
    """
    A ViewSet for managing loan operations.
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Loan.objects.all()

    def get_serializer_class(self):
        return LoanSerializer

    @action(methods=['POST'], detail=False, url_path='grant')
    def grant_loan(self, request):
        """Grant a loan to a bank account"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Loan granted successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'loan_id': {'type': 'integer', 'description': 'ID of the loan'},
                    'repayment_amount': {'type': 'number', 'format': 'decimal', 'description': 'Amount to repay'}
                },
                'required': ['loan_id', 'repayment_amount']
            }
        },
        responses={200: 'Loan repayment successful.', 400: 'Bad request', 404: 'Loan not found'}
    )
    @action(methods=['POST'], detail=False, url_path='repay')
    def repay_loan(self, request):
        """Repay a loan for a bank account"""
        loan_id = request.data.get('loan_id')
        repayment_amount = request.data.get('repayment_amount')

        if not loan_id or not repayment_amount:
            return Response({"detail": "Loan ID and repayment amount are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            loan = Loan.objects.get(id=loan_id, account__user=request.user)
        except Loan.DoesNotExist:
            return Response({"detail": "Loan not found or does not belong to you."},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            repayment_amount = Decimal(repayment_amount)
        except Exception:
            return Response({"detail": "Invalid repayment amount."},
                            status=status.HTTP_400_BAD_REQUEST)

        if repayment_amount <= 0:
            return Response({"detail": "Repayment amount must be greater than zero."},
                            status=status.HTTP_400_BAD_REQUEST)

        if repayment_amount > loan.loan_amount:
            return Response({"detail": "Repayment amount exceeds loan balance."},
                            status=status.HTTP_400_BAD_REQUEST)

        loan.loan_amount -= repayment_amount
        if loan.loan_amount == 0:
            loan.status = 'paid'
        loan.save()

        return Response({"message": "Loan repayment successful."}, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='customer-loans')
    def get_customer_loans(self, request):
        """Retrieve all loans for the authenticated customer"""
        customer_loans = self.queryset.filter(account__user=request.user)
        serializer = self.get_serializer(customer_loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)