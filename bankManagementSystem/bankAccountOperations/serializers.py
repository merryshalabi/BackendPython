
from decimal import Decimal
from rest_framework import serializers
from core.models import BankAccount, Transaction ,Loan ,ForeignCurrency,Bank
from core.utils import convert_to_base_currency

class DepositSerializer(serializers.ModelSerializer):
    account_id = serializers.IntegerField()
    currency = serializers.CharField(max_length=10, default='NIS')

    class Meta:
        model = Transaction
        fields = ('account_id', 'amount', 'currency')
        extra_kwargs = {
            'amount': {'min_value': Decimal('0.01')},
        }

    def validate(self, data):
        """Validates the deposit data"""
        try:
            account = BankAccount.objects.get(pk=data['account_id'], user=self.context['request'].user)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError({"account": "Account does not exist or does not belong to you."})

        if account.status in ['suspended', 'closed']:
            raise serializers.ValidationError({"account": "Account is not active."})

        currency_code = data['currency']
        if currency_code != 'NIS':  # If it's not the base currency, check if it's supported
            if not ForeignCurrency.objects.filter(currency_code=currency_code).exists():
                raise serializers.ValidationError({"currency": f"Unsupported currency: {currency_code}"})

        data['account'] = BankAccount.objects.get(
            pk=data['account_id'],
            user=self.context['request'].user
        )
        return data

    def create(self, validated_data):
        """Creates a deposit transaction, applies the fee, and updates the account balance"""
        account = validated_data['account']
        amount = validated_data['amount']
        currency = validated_data.get('currency', 'NIS')

        if currency != 'NIS':
            try:
                amount = convert_to_base_currency(amount, currency)
            except ValueError as e:
                raise serializers.ValidationError({"currency": str(e)})

        bank = Bank.objects.first()
        if not bank:
            raise serializers.ValidationError({"bank": "Bank instance not found."})

        # Retrieve the fee percentage from the bank settings
        fee_percentage = bank.transaction_fee_percentage
        fee = amount * (fee_percentage / 100)
        net_amount = amount - fee

        account.balance += net_amount
        account.save()

        # Add fee to bank balance
        bank.balance += fee
        bank.save()

        transaction = Transaction.objects.create(
            account=account,
            transaction_type='deposit',
            amount=net_amount,
            fee=fee,
            currency=currency
        )
        return transaction


class WithdrawalSerializer(serializers.ModelSerializer):
    account_id = serializers.IntegerField()
    currency = serializers.CharField(max_length=10, default='NIS')

    class Meta:
        model = Transaction
        fields = ('account_id', 'amount', 'currency')
        extra_kwargs = {
            'amount': {'min_value': 0.01},
        }

    def validate(self, data):
        """Validates the withdrawal data"""
        try:
            account = BankAccount.objects.get(pk=data['account_id'], user=self.context['request'].user)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError({"account": "Account does not exist or does not belong to you."})

        if account.status in ['suspended', 'closed']:
            raise serializers.ValidationError({"account": "Account is not active."})

        currency_code = data['currency']
        if currency_code != 'NIS':
            if not ForeignCurrency.objects.filter(currency_code=currency_code).exists():
                raise serializers.ValidationError({"currency": f"Unsupported currency: {currency_code}"})

        data['account'] = account
        return data

    def create(self, validated_data):
        """Creates a withdrawal transaction, applies the fee, and updates the account balance"""
        account = validated_data['account']
        amount = validated_data['amount']
        currency = validated_data.get('currency', 'NIS')

        if currency != 'NIS':
            try:
                amount = convert_to_base_currency(amount, currency)
            except ValueError as e:
                raise serializers.ValidationError({"currency": str(e)})

        bank = Bank.objects.first()
        if not bank:
            raise serializers.ValidationError({"bank": "Bank instance not found."})

        fee_percentage = bank.transaction_fee_percentage
        fee = amount * (fee_percentage / 100)
        total_amount = amount + fee

        if account.balance < total_amount:
            raise serializers.ValidationError("Insufficient funds.")

        account.balance -= total_amount
        account.save()

        # Add fee to the bank's balance
        bank.balance += fee
        bank.save()

        transaction = Transaction.objects.create(
            account=account,
            transaction_type='withdrawal',
            amount=amount,
            fee=fee,
            currency=currency
        )
        return transaction



class BalanceSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()

    def validate(self, data):
        """Validates the account data."""
        try:
            account = BankAccount.objects.get(pk=data['account_id'])
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Account does not exist.")

        if account.status in ['suspended', 'closed']:
            raise serializers.ValidationError("Cannot retrieve balance for a suspended or closed account.")

        data['account'] = account
        return data


class TransferSerializer(serializers.ModelSerializer):
    source_account_id = serializers.IntegerField()
    target_account_id = serializers.IntegerField()
    currency = serializers.CharField(max_length=10, default='NIS')

    class Meta:
        model = Transaction
        fields = ('source_account_id', 'target_account_id', 'amount', 'currency')
        extra_kwargs = {
            'amount': {'min_value': Decimal('0.01')},
        }

    def validate(self, data):
        """Validates transfer details and ensures source account belongs to the user"""
        user = self.context['request'].user
        source_account_id = data['source_account_id']
        target_account_id = data['target_account_id']
        amount = data['amount']

        # Validate source account with user constraint
        try:
            source_account = BankAccount.objects.get(id=source_account_id, user=user)
            if source_account.balance < amount:
                raise serializers.ValidationError("Insufficient funds in source account.")
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Source account not found or does not belong to you.")

        # Validate target account without user constraint
        try:
            target_account = BankAccount.objects.get(id=target_account_id)
        except BankAccount.DoesNotExist:
            raise serializers.ValidationError("Target account not found.")

        # Fee Calculation
        bank = Bank.objects.first()
        if not bank:
            raise serializers.ValidationError("Bank instance not found.")
        fee_percentage = bank.transaction_fee_percentage
        fee = amount * (fee_percentage / 100)
        total_amount = amount + fee

        if source_account.balance < total_amount:
            raise serializers.ValidationError("Insufficient funds for transfer and fee.")

        # Verify currency
        currency_code = data['currency']
        if currency_code != 'NIS':
            if not ForeignCurrency.objects.filter(currency_code=currency_code).exists():
                raise serializers.ValidationError(f"Unsupported currency: {currency_code}")

        # Add validated accounts for transfer
        data['source_account'] = source_account
        data['target_account'] = target_account
        data['fee'] = fee  # store fee for later use in `create`

        return data

    def create(self, validated_data):
        """Perform the transfer, apply the fee, and update balances"""
        source_account = validated_data['source_account']
        target_account = validated_data['target_account']
        amount = validated_data['amount']
        fee = validated_data['fee']
        currency = validated_data.get('currency', 'NIS')

        # Update account balances
        source_account.balance -= (amount + fee)
        target_account.balance += amount
        source_account.save()
        target_account.save()

        # Update bank balance with fee income
        bank = Bank.objects.first()
        bank.balance += fee
        bank.save()

        # Log transactions
        transaction_out = Transaction.objects.create(
            account=source_account,
            transaction_type='transfer_out',
            amount=amount,
            fee=fee,
            currency=currency,
            target_account=target_account
        )

        Transaction.objects.create(
            account=target_account,
            transaction_type='transfer_in',
            amount=amount,
            currency=currency,
            source_account=source_account
        )

        return transaction_out



class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ('id', 'account', 'loan_amount', 'interest_rate', 'status', 'created_at', 'due_date')
        read_only_fields = ('id', 'created_at', 'interest_rate', 'status')

    def validate(self, data):
        account = data.get('account')
        if not account:
            raise serializers.ValidationError({"account": "This field is required."})

        bank = Bank.objects.first()
        if not bank:
            raise serializers.ValidationError({"bank": "Bank instance not found."})

        loan_amount = data.get('loan_amount')
        if not loan_amount:
            raise serializers.ValidationError({"loan_amount": "This field is required."})

        if loan_amount > bank.balance:
            raise serializers.ValidationError("The bank does not have enough balance to grant this loan.")

        if loan_amount > 5000:
            raise serializers.ValidationError({"loan_amount": "The maximum loan amount is 5,000 NIS."})

        if account.status != 'active':
            raise serializers.ValidationError({"account": "Loan can only be granted to active accounts."})

        return data

    def create(self, validated_data):
        bank = Bank.objects.first()
        loan_amount = validated_data.get('loan_amount')

        interest_rate = bank.interest_rate

        bank.balance -= loan_amount
        bank.save()

        validated_data['interest_rate'] = interest_rate

        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    source_account = serializers.PrimaryKeyRelatedField(queryset=BankAccount.objects.all(), required=False)
    target_account = serializers.PrimaryKeyRelatedField(queryset=BankAccount.objects.all(), required=False)

    class Meta:
        model = Transaction
        fields = ('id', 'account', 'transaction_type', 'amount', 'fee', 'currency', 'created_at', 'source_account', 'target_account')
        read_only_fields = ('id', 'created_at')

    def validate(self, data):
        transaction_type = data.get('transaction_type')
        amount = data.get('amount')
        account = data.get('account')

        if transaction_type == 'transfer_out':
            if not data.get('target_account'):
                raise serializers.ValidationError({"target_account": "Target account is required for transfers."})
            if not data.get('source_account'):
                raise serializers.ValidationError({"source_account": "Source account is required for transfers."})

        if transaction_type in ['deposit', 'withdrawal'] and not account:
            raise serializers.ValidationError({"account": "Account is required for deposits and withdrawals."})

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Transaction amount must be greater than zero."})

        return data

    def create(self, validated_data):
        source_account = validated_data['source_account']
        target_account = validated_data['target_account']
        amount = validated_data['amount']
        currency = validated_data.get('currency', 'NIS')


        bank = Bank.objects.first()
        fee_percentage = bank.transaction_fee_percentage
        fee = amount * (fee_percentage / 100)
        total_amount = amount + fee

        source_account.balance -= total_amount
        target_account.balance += amount
        source_account.save()
        target_account.save()

        transaction_out = Transaction.objects.create(
            account=source_account,
            transaction_type='transfer_out',
            amount=amount,
            fee=fee,
            currency=currency,
            target_account=target_account
        )

        Transaction.objects.create(
            account=target_account,
            transaction_type='transfer_in',
            amount=amount,
            currency=currency,
            source_account=source_account
        )

        return transaction_out
