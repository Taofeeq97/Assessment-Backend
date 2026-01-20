from django.db import models

class ShipmentStatus(models.TextChoices):
    UPLOADED = 'uploaded'
    REVIEWING = 'reviewing'
    READY = 'ready'
    PURCHASED = 'purchased'
    CANCELLED = 'cancelled'


class ShipmentValidationStatus(models.TextChoices):
    PENDING = 'pending'
    VALID = 'valid'
    INVALID = 'invalid'
    WARNING = 'warning'


class ShippingServiceType(models.TextChoices):
    PRIORITY = 'priority'
    GROUND = 'ground'
    EXPRESS = 'express'
    OVERNIGHT = 'overnight'
