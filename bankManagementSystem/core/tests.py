from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models
from decimal import Decimal
from datetime import date, timedelta
from core.models import ForeignCurrency


# Create your tests here.

class ModelTests(TestCase):
    """Test class for our application model"""

    def test_create_user_email_successful(self):
        """Testing creating a new user with email is successful"""

        email = "test@example.com"
        password= "password123"

        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))


    def test_new_user_email_normalized(self):
        """Checks if the email is normalized or not"""

        sample_test = [
            ['test1@Example.com', 'test1@example.com'],
            ['Test2@example.Com', 'Test2@example.com'],
            ['test3@example.com', 'test3@example.com'],
        ]

        for email, expected in sample_test:
            user = get_user_model().objects.create_user(email, 'password123')
            self.assertEqual(user.email, expected)


    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises an error"""

        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'password123')



    def test_create_superuser(self):
        """Tests Creating a superuser is successful"""


        user = get_user_model().objects.create_superuser(
            'test@exmaple.com',
            "pass123"
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_bank_account_successful(self):
        """Test creating a bank account with default values"""
        user = get_user_model().objects.create_user(
            email='template@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='1234567890',
            balance=1000.00
        )

        self.assertEqual(account.user, user)
        self.assertEqual(account.account_number, '1234567890')
        self.assertEqual(account.balance, 1000.00)
        self.assertEqual(account.status, 'active')
        self.assertTrue(account.created_at)

    def test_create_loan_successful(self):
        """Test creating a loan with default values"""
        user = get_user_model().objects.create_user(
            email='loanuser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='9876543210',
            balance=5000.00
        )

        loan_amount = Decimal('1000.00')
        interest_rate = Decimal('5.0')  # 5% interest rate
        due_date = date.today() + timedelta(days=365)  # 1 year loan period

        loan = models.Loan.objects.create(
            account=account,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            due_date=due_date
        )

        self.assertEqual(loan.account, account)
        self.assertEqual(loan.loan_amount, loan_amount)
        self.assertEqual(loan.interest_rate, interest_rate)
        self.assertEqual(loan.status, 'active')
        self.assertEqual(loan.due_date, due_date)
        self.assertTrue(loan.created_at)

    def test_defaulted_loan_status(self):
        """Test changing a loan status to defaulted"""
        user = get_user_model().objects.create_user(
            email='defaulteduser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='1122334455',
            balance=3000.00
        )

        loan = models.Loan.objects.create(
            account=account,
            loan_amount=Decimal('1500.00'),
            interest_rate=Decimal('4.5'),
            due_date=date.today() + timedelta(days=365)
        )

        # Change the loan status to defaulted
        loan.status = 'defaulted'
        loan.save()

        self.assertEqual(loan.status, 'defaulted')

    def test_paid_loan_status(self):
        """Test changing a loan status to paid"""
        user = get_user_model().objects.create_user(
            email='paiduser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='9988776655',
            balance=4000.00
        )

        loan = models.Loan.objects.create(
            account=account,
            loan_amount=Decimal('2000.00'),
            interest_rate=Decimal('3.0'),
            due_date=date.today() + timedelta(days=365)
        )

        # Change the loan status to paid
        loan.status = 'paid'
        loan.save()

        self.assertEqual(loan.status, 'paid')

    def test_create_transaction_deposit(self):
        """Test creating a deposit transaction"""
        user = get_user_model().objects.create_user(
            email='deposituser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='111122223333',
            balance=1000.00
        )

        transaction = models.Transaction.objects.create(
            account=account,
            transaction_type='deposit',
            amount=Decimal('500.00'),
            fee=Decimal('0.0'),  # No fee for this deposit
            description='Deposit to savings account'
        )

        self.assertEqual(transaction.account, account)
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.amount, Decimal('500.00'))
        self.assertEqual(transaction.fee, Decimal('0.0'))
        self.assertEqual(transaction.description, 'Deposit to savings account')
        self.assertTrue(transaction.created_at)

    def test_create_transaction_withdrawal(self):
        """Test creating a withdrawal transaction"""
        user = get_user_model().objects.create_user(
            email='withdrawaluser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='444455556666',
            balance=2000.00
        )

        transaction = models.Transaction.objects.create(
            account=account,
            transaction_type='withdrawal',
            amount=Decimal('300.00'),
            fee=Decimal('5.00'),  # Adding a fee for the withdrawal
            description='Withdrawal from checking account'
        )

        self.assertEqual(transaction.account, account)
        self.assertEqual(transaction.transaction_type, 'withdrawal')
        self.assertEqual(transaction.amount, Decimal('300.00'))
        self.assertEqual(transaction.fee, Decimal('5.00'))
        self.assertEqual(transaction.description, 'Withdrawal from checking account')
        self.assertTrue(transaction.created_at)

    def test_create_transaction_transfer(self):
        """Test creating a transfer transaction"""
        user = get_user_model().objects.create_user(
            email='transferuser@example.com',
            password='password123'
        )
        source_account = models.BankAccount.objects.create(
            user=user,
            account_number='777788889999',
            balance=5000.00
        )
        target_account = models.BankAccount.objects.create(
            user=user,
            account_number='000011112222',
            balance=1000.00
        )

        transaction_out = models.Transaction.objects.create(
            account=source_account,
            transaction_type='transfer_out',
            amount=Decimal('500.00'),
            fee=Decimal('5.00'),  # Adding a fee for the transfer
            description='Transfer to another account',
            target_account=target_account
        )

        transaction_in = models.Transaction.objects.create(
            account=target_account,
            transaction_type='transfer_in',
            amount=Decimal('500.00'),
            fee=Decimal('0.0'),  # No fee for the incoming transfer
            description='Transfer from another account',
            source_account=source_account
        )

        # Test the outgoing transaction
        self.assertEqual(transaction_out.account, source_account)
        self.assertEqual(transaction_out.transaction_type, 'transfer_out')
        self.assertEqual(transaction_out.amount, Decimal('500.00'))
        self.assertEqual(transaction_out.fee, Decimal('5.00'))
        self.assertEqual(transaction_out.target_account, target_account)
        self.assertTrue(transaction_out.created_at)

        # Test the incoming transaction
        self.assertEqual(transaction_in.account, target_account)
        self.assertEqual(transaction_in.transaction_type, 'transfer_in')
        self.assertEqual(transaction_in.amount, Decimal('500.00'))
        self.assertEqual(transaction_in.fee, Decimal('0.0'))
        self.assertEqual(transaction_in.source_account, source_account)
        self.assertTrue(transaction_in.created_at)

    def test_transaction_fee(self):
        """Test that a transaction fee is correctly recorded"""
        user = get_user_model().objects.create_user(
            email='feeuser@example.com',
            password='password123'
        )
        account = models.BankAccount.objects.create(
            user=user,
            account_number='555566667777',
            balance=3000.00
        )

        transaction = models.Transaction.objects.create(
            account=account,
            transaction_type='deposit',
            amount=Decimal('1000.00'),
            fee=Decimal('10.00'),
            description='Deposit with a fee'
        )

        self.assertEqual(transaction.fee, Decimal('10.00'))
        self.assertEqual(transaction.amount, Decimal('1000.00'))
        self.assertEqual(transaction.description, 'Deposit with a fee')
        self.assertTrue(transaction.created_at)

    def test_foreign_currency_creation(self):
        # Create a ForeignCurrency object
        currency = ForeignCurrency.objects.create(
            currency_code='USD',
            exchange_rate=Decimal('3.67')
        )

        # Retrieve the currency object from the database
        retrieved_currency = ForeignCurrency.objects.get(currency_code='USD')

        # Assertions to verify the object was created correctly
        self.assertEqual(retrieved_currency.currency_code, 'USD')
        self.assertEqual(retrieved_currency.exchange_rate, Decimal('3.67'))
        self.assertIsNotNone(retrieved_currency.updated_at)  # Ensure the timestamp is set

