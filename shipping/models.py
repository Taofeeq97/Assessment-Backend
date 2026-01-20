from django.db import models
from django.conf import settings
from base.models import BaseModel
from base.constants import ShipmentStatus, ShipmentValidationStatus, ShippingServiceType    


class ShipmentBatch(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shipment_batches'
    )
    filename = models.CharField(max_length=255, help_text="Original CSV filename")
    status = models.CharField(
        max_length=20,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.UPLOADED
    )
    total_shipments = models.IntegerField(default=0)
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    purchased_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'shipment_batches'
        verbose_name = 'Shipment Batch'
        verbose_name_plural = 'Shipment Batches'
        ordering = ['-created_at']

    def __str__(self):
        return f"Batch {self.filename} - {self.total_shipments} shipments"

    def calculate_total_cost(self):
        """Calculate total cost from all shipments in batch"""
        total = self.shipments.aggregate(
            total=models.Sum('shipping_cost')
        )['total'] or 0.00
        self.total_cost = total
        self.save(update_fields=['total_cost', 'updated_at'])
        return self.total_cost


class Shipment(BaseModel):
    batch = models.ForeignKey(
        ShipmentBatch,
        on_delete=models.CASCADE,
        related_name='shipments'
    )
    
    # Ship From Address
    from_first_name = models.CharField(max_length=100, blank=True)
    from_last_name = models.CharField(max_length=100, blank=True)
    from_address_line1 = models.CharField(max_length=255, blank=True)
    from_address_line2 = models.CharField(max_length=255, blank=True)
    from_city = models.CharField(max_length=100, blank=True)
    from_state = models.CharField(max_length=2, blank=True)
    from_zip_code = models.CharField(max_length=10, blank=True)
    
    # Ship To Address (Required)
    to_first_name = models.CharField(max_length=100)
    to_last_name = models.CharField(max_length=100, blank=True)
    to_address_line1 = models.CharField(max_length=255)
    to_address_line2 = models.CharField(max_length=255, blank=True)
    to_city = models.CharField(max_length=100)
    to_state = models.CharField(max_length=2)
    to_zip_code = models.CharField(max_length=10)
    
    # Package Details
    length = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Length in inches"
    )
    width = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Width in inches"
    )
    height = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Height in inches"
    )
    weight_lbs = models.IntegerField(default=0, help_text="Weight in pounds")
    weight_oz = models.IntegerField(default=0, help_text="Weight in ounces")
    phone_1 = models.CharField(max_length=20, blank=True)
    phone_2 = models.CharField(max_length=20, blank=True)
    order_number = models.CharField(max_length=100, blank=True)
    item_sku = models.CharField(max_length=100, blank=True)
    shipping_service = models.CharField(
        max_length=50,
        blank=True,
        help_text="Selected shipping service"
    )
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    validation_status = models.CharField(
        max_length=20,
        choices=ShipmentValidationStatus.choices,
        default=ShipmentValidationStatus.PENDING
    )
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation errors"
    )
    validation_warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation warnings"
    )
    from_address_validated = models.BooleanField(default=False)
    to_address_validated = models.BooleanField(default=False)
    from_address_validation_result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Address validation API response"
    )
    to_address_validation_result = models.JSONField(
        default=dict,
        blank=True,
        help_text="Address validation API response"
    )
    row_number = models.IntegerField(
        help_text="Original row number in CSV (for reference)"
    )

    class Meta:
        db_table = 'shipments'
        verbose_name = 'Shipment'
        verbose_name_plural = 'Shipments'
        ordering = ['row_number']

    def __str__(self):
        return f"Shipment to {self.to_city}, {self.to_state} - Order #{self.order_number}"

    @property
    def total_weight_oz(self):
        """Calculate total weight in ounces"""
        return (self.weight_lbs * 16) + self.weight_oz

    @property
    def from_address_formatted(self):
        """Return formatted from address"""
        if not self.from_address_line1:
            return "No sender address"
        
        name = f"{self.from_first_name} {self.from_last_name}".strip()
        address2 = f", {self.from_address_line2}" if self.from_address_line2 else ""
        return f"{name}\n{self.from_address_line1}{address2}\n{self.from_city}, {self.from_state} {self.from_zip_code}"

    @property
    def to_address_formatted(self):
        """Return formatted to address"""
        name = f"{self.to_first_name} {self.to_last_name}".strip()
        address2 = f", {self.to_address_line2}" if self.to_address_line2 else ""
        return f"{name}\n{self.to_address_line1}{address2}\n{self.to_city}, {self.to_state} {self.to_zip_code}"

    @property
    def package_details_formatted(self):
        """Return formatted package details"""
        if self.length and self.width and self.height:
            dimensions = f"{self.length}×{self.width}×{self.height} in"
        else:
            dimensions = "No dimensions"
        
        weight = f"{self.weight_lbs} lbs {self.weight_oz} oz"
        return f"{dimensions}\n{weight}"

    def validate_shipment(self):
        """Validate shipment data and set validation status"""
        errors = []
        warnings = []
        if not self.to_first_name:
            errors.append("Recipient first name is required")
        if not self.to_address_line1:
            errors.append("Recipient address is required")
        if not self.to_city:
            errors.append("Recipient city is required")
        if not self.to_state:
            errors.append("Recipient state is required")
        if not self.to_zip_code:
            errors.append("Recipient ZIP code is required")

        if not self.from_address_line1:
            warnings.append("Sender address is missing")

        if not (self.length and self.width and self.height):
            warnings.append("Package dimensions are missing")
        
        if self.weight_lbs == 0 and self.weight_oz == 0:
            warnings.append("Package weight is zero or missing")

        if errors:
            self.validation_status = 'invalid'
        elif warnings:
            self.validation_status = 'warning'
        else:
            self.validation_status = 'valid'

        self.validation_errors = errors
        self.validation_warnings = warnings
        self.save(update_fields=[
            'validation_status',
            'validation_errors',
            'validation_warnings',
            'updated_at'
        ])

        return self.validation_status


class ShippingService(BaseModel):
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=20, choices=ShippingServiceType.choices)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price in USD"
    )
    per_oz_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text="Additional cost per ounce"
    )
    is_active = models.BooleanField(default=True)
    delivery_days_min = models.IntegerField(default=1)
    delivery_days_max = models.IntegerField(default=5)

    class Meta:
        db_table = 'shipping_services'
        verbose_name = 'Shipping Service'
        verbose_name_plural = 'Shipping Services'
        ordering = ['base_price']

    def __str__(self):
        return f"{self.name} - ${self.base_price}"

    def calculate_price(self, weight_oz):
        """Calculate shipping price based on weight"""
        return float(self.base_price) + (float(self.per_oz_rate) * weight_oz)


class LabelPurchase(BaseModel):
    LABEL_SIZE_CHOICES = [
        ('letter', 'Letter/A4 (8.5x11)'),
        ('4x6', '4x6 inch (Thermal)'),
    ]

    batch = models.ForeignKey(
        ShipmentBatch,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='label_purchases'
    )
    label_size = models.CharField(
        max_length=10,
        choices=LABEL_SIZE_CHOICES,
        default='4x6'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_labels = models.IntegerField()
    terms_accepted = models.BooleanField(default=False)
    label_file = models.FileField(
        upload_to='labels/',
        null=True,
        blank=True,
        help_text="Generated label PDF"
    )

    class Meta:
        db_table = 'label_purchases'
        verbose_name = 'Label Purchase'
        verbose_name_plural = 'Label Purchases'
        ordering = ['-created_at']

    def __str__(self):
        return f"Purchase #{self.id} - {self.total_labels} labels - ${self.total_amount}"   