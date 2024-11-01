from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from bankManagementSystem import settings
from decimal import Decimal

# Create your models here.
"""
models
"""
class UserManager(BaseUserManager):
    """User Manager class"""
    def create_user(self, email, password=None, **extra_fields):
        """Creates a user"""
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """Creates a super user"""
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model"""
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'


class BankAccount(models.Model):
    """Bank Account model"""

    ACCOUNT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Reference your custom user model
        on_delete=models.CASCADE,
        related_name='accounts'
    )
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=ACCOUNT_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Account {self.account_number} - {self.user.email}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.0'))
    currency = models.CharField(max_length=10, default='NIS')
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    source_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        related_name='source_transactions',
        blank=True,
        null=True
    )
    target_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        related_name='target_transactions',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} on {self.created_at} for {self.account}"


class Loan(models.Model):
    LOAN_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid', 'Paid'),
        ('defaulted', 'Defaulted'),
    ]

    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # E.g., 5.0 for 5%
    status = models.CharField(max_length=10, choices=LOAN_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()  # You may want to calculate this based on the loan period

    def __str__(self):
        return f"Loan of {self.loan_amount} for account {self.account.account_number}"


class ForeignCurrency(models.Model):
    currency_code = models.CharField(max_length=3, unique=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_code} - Rate: {self.exchange_rate}"

class Bank(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000000.00)
    transaction_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)  # Default transaction fee percentage
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)  # Default interest rate for loans
    def __str__(self):
        return f"Bank Balance: {self.balance} NIS"

