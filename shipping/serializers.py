from rest_framework import serializers
from shipping.models import (
    ShipmentBatch,
    Shipment,
    ShippingService,
    LabelPurchase
)


class ShippingServiceSerializer(serializers.ModelSerializer):
    """Serializer for ShippingService model"""
    delivery_time = serializers.SerializerMethodField()
    
    class Meta:
        model = ShippingService
        fields = [
            'id',
            'name',
            'service_type',
            'description',
            'base_price',
            'per_oz_rate',
            'delivery_days_min',
            'delivery_days_max',
            'delivery_time',
            'is_active'
        ]
        read_only_fields = ['id']
    
    def get_delivery_time(self, obj):
        """Return formatted delivery time"""
        if obj.delivery_days_min == obj.delivery_days_max:
            return f"{obj.delivery_days_min} days"
        return f"{obj.delivery_days_min}-{obj.delivery_days_max} days"


class ShipmentSerializer(serializers.ModelSerializer):
    """Serializer for Shipment model"""
    from_address_formatted = serializers.ReadOnlyField()
    to_address_formatted = serializers.ReadOnlyField()
    package_details_formatted = serializers.ReadOnlyField()
    total_weight_oz = serializers.ReadOnlyField()
    
    class Meta:
        model = Shipment
        fields = [
            'id',
            'batch',
            'row_number',
            # From address
            'from_first_name',
            'from_last_name',
            'from_address_line1',
            'from_address_line2',
            'from_city',
            'from_state',
            'from_zip_code',
            # To address
            'to_first_name',
            'to_last_name',
            'to_address_line1',
            'to_address_line2',
            'to_city',
            'to_state',
            'to_zip_code',
            # Package details
            'length',
            'width',
            'height',
            'weight_lbs',
            'weight_oz',
            # Contact & Reference
            'phone_1',
            'phone_2',
            'order_number',
            'item_sku',
            # Shipping
            'shipping_service',
            'shipping_cost',
            # Validation
            'validation_status',
            'validation_errors',
            'validation_warnings',
            'from_address_validated',
            'to_address_validated',
            # Formatted fields
            'from_address_formatted',
            'to_address_formatted',
            'package_details_formatted',
            'total_weight_oz',
            # Timestamps
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'batch',
            'row_number',
            'validation_status',
            'validation_errors',
            'validation_warnings',
            'from_address_validated',
            'to_address_validated',
            'from_address_formatted',
            'to_address_formatted',
            'package_details_formatted',
            'total_weight_oz',
            'created_at',
            'updated_at'
        ]


class ShipmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating shipments"""
    
    class Meta:
        model = Shipment
        fields = [
            'batch',
            'row_number',
            # From address
            'from_first_name',
            'from_last_name',
            'from_address_line1',
            'from_address_line2',
            'from_city',
            'from_state',
            'from_zip_code',
            # To address
            'to_first_name',
            'to_last_name',
            'to_address_line1',
            'to_address_line2',
            'to_city',
            'to_state',
            'to_zip_code',
            # Package details
            'length',
            'width',
            'height',
            'weight_lbs',
            'weight_oz',
            # Contact & Reference
            'phone_1',
            'phone_2',
            'order_number',
            'item_sku'
        ]


class ShipmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shipments"""
    
    class Meta:
        model = Shipment
        fields = [
            # From address
            'from_first_name',
            'from_last_name',
            'from_address_line1',
            'from_address_line2',
            'from_city',
            'from_state',
            'from_zip_code',
            # To address
            'to_first_name',
            'to_last_name',
            'to_address_line1',
            'to_address_line2',
            'to_city',
            'to_state',
            'to_zip_code',
            # Package details
            'length',
            'width',
            'height',
            'weight_lbs',
            'weight_oz',
            # Contact & Reference
            'phone_1',
            'phone_2',
            'order_number',
            'item_sku',
            # Shipping
            'shipping_service',
            'shipping_cost'
        ]
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.validate_shipment()
        return instance


class BulkUpdateAddressSerializer(serializers.Serializer):
    """Serializer for bulk updating addresses"""
    shipment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text="List of shipment IDs to update"
    )
    address_type = serializers.ChoiceField(
        choices=['from', 'to'],
        required=True,
        help_text="Which address to update (from or to)"
    )
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    address_line1 = serializers.CharField(max_length=255, required=True)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=True)
    state = serializers.CharField(max_length=2, required=True)
    zip_code = serializers.CharField(max_length=10, required=True)


class BulkUpdatePackageSerializer(serializers.Serializer):
    """Serializer for bulk updating package details"""
    shipment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text="List of shipment IDs to update"
    )
    length = serializers.DecimalField(max_digits=6, decimal_places=2, required=True)
    width = serializers.DecimalField(max_digits=6, decimal_places=2, required=True)
    height = serializers.DecimalField(max_digits=6, decimal_places=2, required=True)
    weight_lbs = serializers.IntegerField(required=True)
    weight_oz = serializers.IntegerField(required=True)


class BulkUpdateShippingServiceSerializer(serializers.Serializer):
    """Serializer for bulk updating shipping services"""
    shipment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        help_text="List of shipment IDs to update"
    )
    action = serializers.ChoiceField(
        choices=['cheapest', 'priority', 'ground'],
        required=True,
        help_text="Action to perform"
    )


class ShipmentBatchSerializer(serializers.ModelSerializer):
    """Serializer for ShipmentBatch model"""
    shipments = ShipmentSerializer(many=True, read_only=True)
    shipment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ShipmentBatch
        fields = [
            'id',
            'filename',
            'status',
            'total_shipments',
            'total_cost',
            'shipment_count',
            'shipments',
            'created_at',
            'updated_at',
            'purchased_at'
        ]
        read_only_fields = [
            'id',
            'total_shipments',
            'total_cost',
            'created_at',
            'updated_at',
            'purchased_at'
        ]
    
    def get_shipment_count(self, obj):
        """Return actual count of shipments"""
        return obj.shipments.count()


class ShipmentBatchListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for batch list (without shipments)"""
    shipment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ShipmentBatch
        fields = [
            'id',
            'filename',
            'status',
            'total_shipments',
            'total_cost',
            'shipment_count',
            'created_at',
            'updated_at',
            'purchased_at'
        ]
        read_only_fields = [
            'id',
            'total_shipments',
            'total_cost',
            'created_at',
            'updated_at',
            'purchased_at'
        ]
    
    def get_shipment_count(self, obj):
        """Return actual count of shipments"""
        return obj.shipments.count()


class ShipmentBatchCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating batches"""
    
    class Meta:
        model = ShipmentBatch
        fields = ['filename']


class LabelPurchaseSerializer(serializers.ModelSerializer):
    """Serializer for LabelPurchase model"""
    
    class Meta:
        model = LabelPurchase
        fields = [
            'id',
            'batch',
            'label_size',
            'total_amount',
            'total_labels',
            'terms_accepted',
            'label_file'
        ]
        read_only_fields = [
            'id',
            'total_amount',
            'total_labels',
            'label_file'
        ]
    
    def validate_terms_accepted(self, value):
        """Ensure terms are accepted"""
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions")
        return value


class LabelPurchaseCreateSerializer(serializers.Serializer):
    """Serializer for creating label purchases"""
    batch_id = serializers.IntegerField(required=True)
    label_size = serializers.ChoiceField(
        choices=['letter', '4x6'],
        required=True
    )
    terms_accepted = serializers.BooleanField(required=True)
    
    def validate_terms_accepted(self, value):
        """Ensure terms are accepted"""
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions")
        return value


class CalculateShippingSerializer(serializers.Serializer):
    """Serializer for calculating shipping costs"""
    shipment_id = serializers.UUIDField(required=True)
    service_id = serializers.UUIDField(required=True)