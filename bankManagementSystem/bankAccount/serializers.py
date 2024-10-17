from rest_framework import serializers
from core.models import BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for the BankAccount model."""

    class Meta:
        model = BankAccount
        fields = ('id', 'account_number', 'balance', 'status', 'created_at')
        read_only_fields = ('id', 'created_at', 'balance')

    def create(self, validated_data):
        """Create a new bank account."""
        # mish mt2kdi mn had elstr
        validated_data['user'] = self.context['request'].user
        return BankAccount.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update a bank account, only status can be updated."""
        # Only allow updating the status (e.g., suspend or close)
        instance.status = validated_data.get('status', instance.status)

        # Business rule: Only close an account if the balance is non-negative
        if instance.status == 'closed' and instance.balance < 0:
            raise serializers.ValidationError("Account cannot be closed with a negative balance.")

        instance.save()
        return instance