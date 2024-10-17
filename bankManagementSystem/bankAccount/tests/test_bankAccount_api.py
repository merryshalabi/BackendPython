from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from core.models import BankAccount

# Helper function to generate URLs for bank account detail
def bankaccount_detail_url(account_id):
    """Create and return a bank account detail URL"""
    return reverse('bankaccount-detail', args=[account_id])

def bankaccount_suspend_url(account_id):
    """Create and return the URL for suspending a bank account"""
    return reverse('bankaccount-suspend', args=[account_id])

def bankaccount_close_url(account_id):
    """Create and return the URL for closing a bank account"""
    return reverse('bankaccount-close', args=[account_id])


class PublicBankAccountAPITests(TestCase):
    """Test the publicly available bank account API"""

    def setUp(self):
        self.client = APIClient()

    def test_authentication_required(self):
        """Test that authentication is required for accessing the API"""
        res = self.client.get(reverse('bankaccount-list'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateBankAccountAPITests(TestCase):
    """Test the authenticated bank account API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='password123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_bank_accounts(self):
        """Test retrieving bank accounts for authenticated user"""
        BankAccount.objects.create(user=self.user, account_number='1234567890')
        BankAccount.objects.create(user=self.user, account_number='9876543210')

        res = self.client.get(reverse('bankaccount-list'))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_bank_accounts_limited_to_user(self):
        """Test that bank accounts are limited to the authenticated user"""
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='password123'
        )
        BankAccount.objects.create(user=other_user, account_number='5555555555')
        BankAccount.objects.create(user=self.user, account_number='1234567890')

        res = self.client.get(reverse('bankaccount-list'))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_bank_account(self):
        """Test creating a bank account"""
        payload = {
            'account_number': '1234567890',
            'status': 'active'
        }
        res = self.client.post(reverse('bankaccount-list'), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        bank_account = BankAccount.objects.get(id=res.data['id'])
        self.assertEqual(bank_account.account_number, payload['account_number'])
        self.assertEqual(bank_account.user, self.user)

    def test_suspend_bank_account(self):
        """Test suspending a bank account"""
        bank_account = BankAccount.objects.create(
            user=self.user,
            account_number='1234567890',
            status='active'
        )

        url = bankaccount_suspend_url(bank_account.id)
        res = self.client.patch(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        bank_account.refresh_from_db()
        self.assertEqual(bank_account.status, 'suspended')

    def test_close_bank_account(self):
        """Test closing a bank account"""
        bank_account = BankAccount.objects.create(
            user=self.user,
            account_number='1234567890',
            status='active',
            balance=0
        )

        url = bankaccount_close_url(bank_account.id)
        res = self.client.patch(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        bank_account.refresh_from_db()
        self.assertEqual(bank_account.status, 'closed')

    def test_close_bank_account_with_negative_balance(self):
        """Test closing a bank account with a negative balance fails"""
        bank_account = BankAccount.objects.create(
            user=self.user,
            account_number='1234567890',
            status='active',
            balance=-100.00
        )

        url = bankaccount_close_url(bank_account.id)
        res = self.client.patch(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        bank_account.refresh_from_db()
        self.assertEqual(bank_account.status, 'active')

    def test_suspend_already_suspended_account(self):
        """Test suspending an already suspended account fails"""
        bank_account = BankAccount.objects.create(
            user=self.user,
            account_number='1234567890',
            status='suspended'
        )

        url = bankaccount_suspend_url(bank_account.id)
        res = self.client.patch(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_close_already_closed_account(self):
        """Test closing an already closed account fails"""
        bank_account = BankAccount.objects.create(
            user=self.user,
            account_number='1234567890',
            status='closed'
        )

        url = bankaccount_close_url(bank_account.id)
        res = self.client.patch(url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
