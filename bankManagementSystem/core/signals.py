
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from core.models import Bank

@receiver(post_migrate)
def create_bank(sender, **kwargs):
    if not Bank.objects.exists():
        Bank.objects.create(balance=10000000.00)
