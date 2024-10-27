from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import BankAccount, Transaction


def create_bank_account(user, **params):
    """Helper function to create a bank account"""
    defaults = {
        'account_number': '1234567890',
        'balance': Decimal('1000.00'),
        'status': 'active'
    }
    defaults.update(params)
    return BankAccount.objects.create(user=user, **defaults)


class PrivateBankOperationsTest(APITestCase):
    """Test authenticated access to bank operations"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='user@example.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)

        self.account1 = create_bank_account(user=self.user, account_number='1234567890', balance=1000.00)
        self.account2 = create_bank_account(user=self.user, account_number='0987654321', balance=500.00)

    def test_deposit_success(self):
        """Test a successful deposit and transaction saving"""
        deposit_url = reverse('bankAccountOperations:bankaccounts-deposit')
        payload = {'account_id': self.account1.id, 'amount': '200.00'}
        res = self.client.post(deposit_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify the balance
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('1200.00'))

        # Verify the transaction is recorded
        transaction = Transaction.objects.filter(account=self.account1).latest('created_at')
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.amount, Decimal('200.00'))

    def test_withdraw_success(self):
        """Test a successful withdrawal and transaction saving"""
        withdraw_url = reverse('bankAccountOperations:bankaccounts-withdraw')
        payload = {'account_id': self.account1.id, 'amount': '200.00'}
        res = self.client.post(withdraw_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify the balance
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('800.00'))

        # Verify the transaction is recorded
        transaction = Transaction.objects.filter(account=self.account1).latest('created_at')
        self.assertEqual(transaction.transaction_type, 'withdrawal')
        self.assertEqual(transaction.amount, Decimal('200.00'))

    def test_transfer_success(self):
        """Test a successful transfer and transaction saving"""
        transfer_url = reverse('bankAccountOperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '300.00'
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify balances
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('700.00'))
        self.assertEqual(self.account2.balance, Decimal('800.00'))

        # Verify the transaction for the source account
        transaction_out = Transaction.objects.filter(account=self.account1).latest('created_at')
        self.assertEqual(transaction_out.transaction_type, 'transfer_out')
        self.assertEqual(transaction_out.amount, Decimal('300.00'))

        # Verify the transaction for the target account
        try:
            transaction_in = Transaction.objects.filter(account=self.account2).latest('created_at')
            self.assertEqual(transaction_in.transaction_type, 'transfer_in')
            self.assertEqual(transaction_in.amount, Decimal('300.00'))
        except Transaction.DoesNotExist:
            self.fail("Transaction for the target account (transfer_in) was not created.")
    def test_balance_retrieval_success(self):
        """Test retrieving the balance of an account"""
        balance_url = f"{reverse('bankAccountOperations:bankaccounts-balance')}?account_id={self.account1.id}"
        res = self.client.get(balance_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data['balance']), float(self.account1.balance))

    def test_transaction_recording_for_failed_withdrawal(self):
        """Test that no transaction is recorded for failed withdrawals"""
        withdraw_url = reverse('bankAccountOperations:bankaccounts-withdraw')
        payload = {'account_id': self.account1.id, 'amount': '2000.00'}  # Insufficient funds
        res = self.client.post(withdraw_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Ensure no transaction was recorded
        transactions = Transaction.objects.filter(account=self.account1, transaction_type='withdrawal')
        self.assertEqual(transactions.count(), 0)

    def test_transaction_recording_for_failed_transfer(self):
        """Test that no transaction is recorded for failed transfers"""
        transfer_url = reverse('bankAccountOperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '2000.00'  # Insufficient funds
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Ensure no transaction was recorded
        transactions = Transaction.objects.filter(account=self.account1, transaction_type='transfer_out')
        self.assertEqual(transactions.count(), 0)

    def test_transaction_recording_for_fee(self):
        """Test that the fee is correctly applied and recorded for a transfer"""
        transfer_url = reverse('bankAccountOperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '200.00',
            'fee_percentage': '2.0'  # 2% fee
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Verify balances considering the fee
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('796.00'))  # 200 + 4 (2% fee) = 204 deducted
        self.assertEqual(self.account2.balance, Decimal('700.00'))

        # Verify the transaction for the source account includes the fee
        transaction_out = Transaction.objects.filter(account=self.account1).latest('created_at')
        self.assertEqual(transaction_out.transaction_type, 'transfer_out')
        self.assertEqual(transaction_out.amount, Decimal('200.00'))
        self.assertEqual(transaction_out.fee, Decimal('4.00'))
