from django.db import models
from django.contrib.auth.models import AbstractUser
from base.models import BaseModel


class User(AbstractUser):
    """Extended User model with account balance"""
    account_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Account balance in USD"
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.username} (${self.account_balance})"


class SavedAddress(BaseModel):
    """Saved addresses for quick selection"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_addresses'
    )
    name = models.CharField(max_length=255, help_text="Address nickname/name")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, help_text="Two-letter state code")
    zip_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'saved_addresses'
        verbose_name = 'Saved Address'
        verbose_name_plural = 'Saved Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

    def save(self, *args, **kwargs):
        if self.is_default:
            SavedAddress.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class SavedPackage(BaseModel):
    """Saved package presets for quick selection"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_packages'
    )
    name = models.CharField(max_length=255, help_text="Package preset name")
    length = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Length in inches"
    )
    width = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Width in inches"
    )
    height = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Height in inches"
    )
    weight_lbs = models.IntegerField(default=0, help_text="Weight in pounds")
    weight_oz = models.IntegerField(default=0, help_text="Weight in ounces")
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'saved_packages'
        verbose_name = 'Saved Package'
        verbose_name_plural = 'Saved Packages'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.length}x{self.width}x{self.height}"

    @property
    def total_weight_oz(self):
        """Calculate total weight in ounces"""
        return (self.weight_lbs * 16) + self.weight_oz

    def save(self, *args, **kwargs):
        if self.is_default:
            SavedPackage.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)