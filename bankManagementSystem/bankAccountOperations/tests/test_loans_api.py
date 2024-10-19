from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import BankAccount, Loan

def create_bank_account(user, **params):
    """Helper function to create a bank account"""
    defaults = {
        'account_number': '1234567890',
        'balance': Decimal('1000.00'),
        'status': 'active'
    }
    defaults.update(params)
    return BankAccount.objects.create(user=user, **defaults)

class PrivateLoanOperationsTest(APITestCase):
    """Test authenticated access to loan operations"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='user@example.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        self.account = create_bank_account(user=self.user, balance=Decimal('1000.00'))

        # URLs for loan operations
        self.grant_loan_url = reverse('bankAccountOperations:loans-grant-loan')
        self.repay_loan_url = reverse('bankAccountOperations:loans-repay-loan')

    def test_grant_loan(self):
        """Test granting a loan successfully"""
        payload = {
            'account': self.account.id,  # Use 'account' instead of 'account_id'
            'loan_amount': '5000.00',
            'interest_rate': '5.0',
            'due_date': (date.today() + timedelta(days=365)).isoformat()
        }
        res = self.client.post(self.grant_loan_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        loan = Loan.objects.get(account=self.account)
        self.assertEqual(loan.loan_amount, Decimal('5000.00'))
        self.assertEqual(loan.status, 'active')
        self.assertEqual(loan.interest_rate, Decimal('5.0'))

    def test_grant_loan_exceeding_bank_balance(self):
        """Test error when loan amount exceeds bank balance"""
        payload = {
            'account': self.account.id,  # Use 'account' instead of 'account_id'
            'loan_amount': str(Decimal('10000001.00')),  # Exceeding the bank's balance but within max loan limit
            'interest_rate': '5.0',
            'due_date': (date.today() + timedelta(days=365)).isoformat()
        }
        res = self.client.post(self.grant_loan_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The bank does not have enough balance to grant this loan.', str(res.data))

    def test_repay_loan(self):
        """Test repaying a loan"""
        loan = Loan.objects.create(
            account=self.account,
            loan_amount=Decimal('1000.00'),
            interest_rate=Decimal('5.0'),
            due_date=date.today() + timedelta(days=365)
        )

        payload = {'loan_id': loan.id, 'repayment_amount': '1000.00'}
        res = self.client.post(self.repay_loan_url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.status, 'paid')
