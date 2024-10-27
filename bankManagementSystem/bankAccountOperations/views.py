from decimal import Decimal
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter, OpenApiTypes
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import BankAccount, Loan, Transaction ,Bank
from .serializers import DepositSerializer, WithdrawalSerializer, BalanceSerializer, TransferSerializer, LoanSerializer,TransactionSerializer


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
            transaction = serializer.save()
            return Response({
                "message": "Deposit successful",
                "transaction_id": transaction.id,
                "amount": transaction.amount,
                "fee": transaction.fee
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False, url_path='withdraw')
    def withdraw(self, request):
        """Handle withdrawal from a bank account"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            return Response({
                "message": "Withdrawal successful",
                "transaction_id": transaction.id,
                "amount": transaction.amount,
                "fee": transaction.fee
            }, status=status.HTTP_200_OK)
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
        """Transfer funds between accounts using account IDs."""
        serializer = TransferSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()  # `transaction` is a `Transaction` instance
            return Response({
                "message": "Transfer successful",
                "transaction_id": transaction.id,
                "source_account_id": transaction.account.id,  # Use ID instead of account number
                "target_account_id": transaction.target_account.id,  # Use ID instead of account number
                "amount": str(transaction.amount),
                "fee": str(transaction.fee),
                "currency": transaction.currency
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='account_id',
                description='ID of the bank account to filter transactions',
                required=False,
                type=OpenApiTypes.INT
            )
        ],
        responses={200: TransactionSerializer(many=True)},
    )
    @action(methods=['GET'], detail=False, url_path='transactions')
    def get_all_transactions(self, request):
        """Retrieve all transactions for the authenticated customer, optionally filtered by account."""
        user = request.user
        account_id = request.query_params.get('account_id')

        # Filter transactions by the user and optionally by account_id if provided
        if account_id:
            transactions = Transaction.objects.filter(account__user=user, account__id=account_id).order_by(
                '-created_at')
        else:
            transactions = Transaction.objects.filter(account__user=user).order_by('-created_at')

        # Support pagination if enabled
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Return the full list of transactions if pagination is not applied
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            loan = serializer.save()

            # Set interest rate and fee based on the bank's current values
            bank = Bank.objects.first()
            if not bank:
                return Response({"detail": "Bank instance not found."},
                                status=status.HTTP_400_BAD_REQUEST)
            loan.interest_rate = bank.interest_rate
            loan.save()

            # Add loan amount to the user's account balance
            loan.account.balance += loan.loan_amount
            loan.account.save()

            return Response({
                "id": loan.id,
                "account": loan.account.id,
                "loan_amount": str(loan.loan_amount),
                "interest_rate": str(loan.interest_rate),
                "status": loan.status,
                "created_at": loan.created_at.isoformat(),
                "due_date": loan.due_date.isoformat()
            }, status=status.HTTP_200_OK)
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

        # Calculate interest on the repayment amount
        interest = repayment_amount * (loan.interest_rate / 100)
        total_repayment = repayment_amount + interest

        # Ensure the account has enough funds for the repayment
        if loan.account.balance < total_repayment:
            return Response({"detail": "Insufficient funds in the account for repayment."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Deduct from the borrower's account balance
        loan.account.balance -= total_repayment
        loan.account.save()

        # Deduct repayment from the loan amount
        loan.loan_amount -= repayment_amount
        if loan.loan_amount <= 0:
            loan.status = 'paid'
        loan.save()

        # Add the total repayment to the bank’s balance
        bank = Bank.objects.first()
        if not bank:
            return Response({"detail": "Bank instance not found."},
                            status=status.HTTP_400_BAD_REQUEST)

        bank.balance += total_repayment
        bank.save()

        return Response({
            "message": "Loan repayment successful.",
            "repayment_amount": repayment_amount,
            "interest": interest,
            "total_deducted": total_repayment
        }, status=status.HTTP_200_OK)
    @action(methods=['GET'], detail=False, url_path='customer-loans')
    def get_customer_loans(self, request):
        """Retrieve all loans for the authenticated customer"""
        customer_loans = self.queryset.filter(account__user=request.user)
        serializer = self.get_serializer(customer_loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

