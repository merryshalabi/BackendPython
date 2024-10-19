from rest_framework import serializers
from core.models import BankAccount, Transaction


from decimal import Decimal  # Add this import
from rest_framework import serializers
from core.models import BankAccount, Transaction ,Loan




class DepositSerializer(serializers.ModelSerializer):
    account_id = serializers.IntegerField()

    class Meta:
        model = Transaction
        fields = ('account_id', 'amount')
        extra_kwargs = {
            'amount': {'min_value': Decimal('0.01')},
        }

    def validate(self, data):
        """Validates the deposit data"""
        try:
            # Ensure the account belongs to the authenticated user
            account = BankAccount.objects.get(pk=data['account_id'], user=self.context['request'].user)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError({"account": "Account does not exist or does not belong to you."})

        if account.status == 'suspended':
            raise serializers.ValidationError({"account": "Account is suspended."})
        if account.status == 'closed':
            raise serializers.ValidationError({"account": "Account is closed and cannot accept deposits."})

        data['account'] = account  # Add the account to the validated data
        return data

    def create(self, validated_data):
        """Creates a deposit transaction and updates the account balance"""
        account = validated_data['account']
        amount = validated_data['amount']

        account.balance += amount
        account.save()

        transaction = Transaction.objects.create(
            account=account,
            transaction_type='deposit',
            amount=amount
        )
        return transaction


class WithdrawalSerializer(serializers.ModelSerializer):
    """Serializer for withdrawal operations"""

    account_id = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        source='account'
    )

    class Meta:
        model = Transaction
        fields = ('account_id', 'amount')
        extra_kwargs = {
            'amount': {'min_value': 0.01},
        }

    def validate(self, data):
        """Validates the withdrawal data"""
        account = data['account']
        amount = data['amount']

        if account.status == 'suspended':
            raise serializers.ValidationError("Account is suspended.")
        if account.status == 'closed':
            raise serializers.ValidationError("Account is closed and cannot process withdrawals.")
        if account.balance < amount:
            raise serializers.ValidationError("Insufficient funds.")

        return data

    def create(self, validated_data):
        """Creates a withdrawal transaction and updates the account balance"""
        account = validated_data['account']
        amount = validated_data['amount']

        account.balance -= amount
        account.save()

        transaction = Transaction.objects.create(
            account=account,
            transaction_type='withdrawal',
            amount=amount
        )
        return transaction


class BalanceSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()

    def validate(self, data):
        """
        Validates the account data. It checks:
        - If the account exists.
        - If the account is not suspended or closed.
        """
        try:
            account = BankAccount.objects.get(pk=data['account_id'])
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Account does not exist.")

        if account.status == 'suspended' or account.status == 'closed':
            raise serializers.ValidationError("Cannot retrieve balance for a suspended or closed account.")

        data['account'] = account  # Add the account to the validated data
        return data


class TransferSerializer(serializers.ModelSerializer):
    """Serializer for transfer operations between two bank accounts"""

    source_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        source='source_account'
    )
    target_account_id = serializers.PrimaryKeyRelatedField(
        queryset=BankAccount.objects.all(),
        source='target_account'
    )

    class Meta:
        model = Transaction
        fields = ('source_account_id', 'target_account_id', 'amount')
        extra_kwargs = {
            'amount': {'min_value': 0.01},
        }

    def validate(self, data):
        """Validates the transfer data"""
        source_account = data['source_account']
        target_account = data['target_account']
        amount = data['amount']

        if source_account.status in ['suspended', 'closed']:
            raise serializers.ValidationError("Source account is not active.")
        if target_account.status in ['suspended', 'closed']:
            raise serializers.ValidationError("Target account is not active.")
        if source_account.balance < amount:
            raise serializers.ValidationError("Insufficient funds in the source account.")

        return data

    def create(self, validated_data):
        """Creates a transfer transaction and updates the balances of the accounts"""
        source_account = validated_data['source_account']
        target_account = validated_data['target_account']
        amount = validated_data['amount']

        source_account.balance -= amount
        target_account.balance += amount
        source_account.save()
        target_account.save()

        # Record transactions for both accounts
        Transaction.objects.create(
            account=source_account,
            transaction_type='transfer_out',
            amount=amount
        )
        Transaction.objects.create(
            account=target_account,
            transaction_type='transfer_in',
            amount=amount
        )

        return {"source_account": source_account.id, "target_account": target_account.id}


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ('id', 'account', 'loan_amount', 'interest_rate', 'status', 'created_at', 'due_date')

    def validate(self, data):
        account = data.get('account')
        if not account:
            raise serializers.ValidationError({"account": "This field is required."})

        bank_balance = 10000000  # Bank balance could be stored in a configuration model or settings

        loan_amount = data.get('loan_amount')
        if not loan_amount:
            raise serializers.ValidationError({"loan_amount": "This field is required."})

        # Ensure the bank has enough balance to cover the loan
        if loan_amount > bank_balance:
            raise serializers.ValidationError("The bank does not have enough balance to grant this loan.")

        if loan_amount > 50000:
            raise serializers.ValidationError({"loan_amount": "The maximum loan amount is 50,000 NIS."})

        if account.status != 'active':
            raise serializers.ValidationError({"account": "Loan can only be granted to active accounts."})

        return data
