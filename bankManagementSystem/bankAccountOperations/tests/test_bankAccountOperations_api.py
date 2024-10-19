from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import BankAccount


def create_bank_account(user, **params):
    """Helper function to create a bank account"""
    defaults = {
        'account_number': '1234567890',
        'balance': Decimal('1000.00'),
        'status': 'active'
    }
    defaults.update(params)
    return BankAccount.objects.create(user=user, **defaults)


class PublicBankOperationsTest(APITestCase):
    """Test public access to bank operations (unauthenticated access)"""

    def test_authentication_required(self):
        """Test that authentication is required for all bank operations"""
        deposit_url = reverse('bankoperations:bankaccounts-deposit')
        withdraw_url = reverse('bankoperations:bankaccounts-withdraw')
        balance_url = reverse('bankoperations:bankaccounts-balance')
        transfer_url = reverse('bankoperations:bankaccounts-transfer')

        res = self.client.post(deposit_url, {'account_id': 1, 'amount': 100})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.post(withdraw_url, {'account_id': 1, 'amount': 100})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.get(balance_url, {'account_id': 1})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.post(transfer_url, {
            'source_account_id': 1,
            'target_account_id': 2,
            'amount': 100
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


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
        """Test a successful deposit"""
        deposit_url = reverse('bankoperations:bankaccounts-deposit')
        payload = {'account_id': self.account1.id, 'amount': '200.00'}
        res = self.client.post(deposit_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('1200.00'))

    def test_deposit_to_closed_account(self):
        """Test depositing into a closed account"""
        self.account1.status = 'closed'
        self.account1.save()
        deposit_url = reverse('bankoperations:bankaccounts-deposit')
        payload = {'account_id': self.account1.id, 'amount': '100.00'}
        res = self.client.post(deposit_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Account is closed', str(res.data.get('account', '')))

    def test_withdraw_success(self):
        """Test a successful withdrawal"""
        withdraw_url = reverse('bankoperations:bankaccounts-withdraw')
        payload = {'account_id': self.account1.id, 'amount': '200.00'}
        res = self.client.post(withdraw_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('800.00'))

    def test_withdraw_insufficient_funds(self):
        """Test withdrawing more than the available balance"""
        withdraw_url = reverse('bankoperations:bankaccounts-withdraw')
        payload = {'account_id': self.account1.id, 'amount': '2000.00'}
        res = self.client.post(withdraw_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient funds', str(res.data))

    def test_balance_retrieval_success(self):
        """Test retrieving the balance of an account"""
        balance_url = f"{reverse('bankoperations:bankaccounts-balance')}?account_id={self.account1.id}"
        res = self.client.get(balance_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data['balance']), float(self.account1.balance))

    def test_balance_retrieval_closed_account(self):
        """Test retrieving the balance of a closed account"""
        self.account1.status = 'closed'
        self.account1.save()
        balance_url = f"{reverse('bankoperations:bankaccounts-balance')}?account_id={self.account1.id}"
        res = self.client.get(balance_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot retrieve balance for a suspended or closed account', str(res.data))

    def test_transfer_success(self):
        """Test a successful transfer between two accounts"""
        transfer_url = reverse('bankoperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '300.00'
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('700.00'))
        self.assertEqual(self.account2.balance, Decimal('800.00'))

    def test_transfer_insufficient_funds(self):
        """Test a transfer with insufficient funds"""
        transfer_url = reverse('bankoperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '2000.00'
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient funds in the source account', str(res.data))

    def test_transfer_to_closed_account(self):
        """Test transferring funds to a closed account"""
        self.account2.status = 'closed'
        self.account2.save()
        transfer_url = reverse('bankoperations:bankaccounts-transfer')
        payload = {
            'source_account_id': self.account1.id,
            'target_account_id': self.account2.id,
            'amount': '100.00'
        }
        res = self.client.post(transfer_url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Target account is not active', str(res.data))
