from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.utils import timezone
from shipping.models import ShipmentBatch, Shipment, ShippingService, LabelPurchase
from shipping.serializers import (
    ShipmentBatchSerializer,
    ShipmentBatchListSerializer,
    ShipmentBatchCreateSerializer,
    ShipmentSerializer,
    ShipmentUpdateSerializer,
    BulkUpdateAddressSerializer,
    BulkUpdatePackageSerializer,
    BulkUpdateShippingServiceSerializer,
    LabelPurchaseSerializer,
    LabelPurchaseCreateSerializer,
    CalculateShippingSerializer,
    ShippingServiceSerializer
)
from shipping.utils import CSVParser, AddressValidator
from base.response import APIResponse
import logging

logger = logging.getLogger(__name__)


class ShipmentBatchListView(generics.ListAPIView):
    """
    List all batches for current user
    GET /api/v1/batches/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShipmentBatchListSerializer
    
    def get_queryset(self):
        return ShipmentBatch.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"User {request.user.username} listing batches")
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            logger.info(f"Found {queryset.count()} batches for user {request.user.username}")
            
            return APIResponse.success(
                message="Batches retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            logger.error(f"Error listing batches: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve batches",
                errors=str(e)
            )


class ShipmentBatchDetailView(generics.RetrieveAPIView):
    """
    Get a specific batch with all shipments
    GET /api/v1/batches/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShipmentBatchSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return ShipmentBatch.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            logger.info(f"User {request.user.username} retrieving batch {instance.id}")
            
            serializer = self.get_serializer(instance)
            
            return APIResponse.success(
                message="Batch retrieved successfully",
                data=serializer.data
            )
        except ShipmentBatch.DoesNotExist:
            logger.warning(f"Batch not found")
            return APIResponse.not_found("Batch not found")
        except Exception as e:
            logger.error(f"Error retrieving batch: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve batch",
                errors=str(e)
            )


class UploadCSVView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
            logger.info(f"User {request.user.username} uploading CSV file")
            
            if 'file' not in request.FILES:
                logger.error("No file provided in request")
                return APIResponse.validation_error(
                    message="No file provided"
                )
            
            csv_file = request.FILES['file']
            
            # Validate file type
            if not csv_file.name.endswith('.csv'):
                logger.error(f"Invalid file type: {csv_file.name}")
                return APIResponse.validation_error(
                    message="File must be a CSV"
                )
            
            # Read and decode file
            file_data = csv_file.read().decode('utf-8')
            logger.info(f"CSV file '{csv_file.name}' read successfully. Size: {len(file_data)} bytes")
            
            # Parse CSV
            parser = CSVParser(file_data)
            shipments_data = parser.parse()
            
            logger.info(f"Parsed {len(shipments_data)} shipments from CSV")
            
            if not shipments_data:
                logger.warning("No valid shipment data found in CSV")
                return APIResponse.validation_error(
                    message="No valid shipment data found in CSV"
                )
            
            # Create batch and shipments in a transaction
            with transaction.atomic():
                # Create batch
                batch = ShipmentBatch.objects.create(
                    user=request.user,
                    filename=csv_file.name,
                    status='uploaded',
                    total_shipments=len(shipments_data)
                )
                
                logger.info(f"Created batch {batch.id} for {len(shipments_data)} shipments")
                
                # Create shipments
                shipments_created = 0
                for shipment_data in shipments_data:
                    shipment = Shipment.objects.create(
                        batch=batch,
                        **shipment_data
                    )
                    # Validate each shipment
                    shipment.validate_shipment()
                    shipments_created += 1
                
                logger.info(f"Created {shipments_created} shipments in batch {batch.id}")
                
                # Update batch status
                batch.status = 'reviewing'
                batch.save()
                
                logger.info(f"Batch {batch.id} status updated to 'reviewing'")
            
            # Return batch with shipments
            serializer = ShipmentBatchSerializer(batch)
            return APIResponse.created(
                message="CSV uploaded and processed successfully",
                data=serializer.data
            )
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}", exc_info=True)
            return APIResponse.error(
                message=f"Error parsing CSV: {str(e)}",
                errors=str(e)
            )


class ValidateAddressesView(APIView):
    """
    Validate all addresses in a batch
    POST /api/v1/batches/{id}/validate-addresses/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        try:
            batch = ShipmentBatch.objects.get(id=id, user=request.user)
            logger.info(f"User {request.user.username} validating addresses for batch {batch.id}")
            
            validator = AddressValidator()
            shipments = batch.shipments.all()
            
            validated_count = 0
            failed_count = 0
            
            for shipment in shipments:
                try:
                    # Validate "To" address (required)
                    if shipment.to_address_line1:
                        logger.info(f"Validating 'To' address for shipment {shipment.id}")
                        to_result = validator.validate_address(
                            address_line1=shipment.to_address_line1,
                            address_line2=shipment.to_address_line2,
                            city=shipment.to_city,
                            state=shipment.to_state,
                            zip_code=shipment.to_zip_code
                        )
                        
                        if to_result['valid']:
                            shipment.to_address_validated = True
                            shipment.to_address_validation_result = to_result
                            validated_count += 1
                            logger.info(f"'To' address validated for shipment {shipment.id}")
                        else:
                            logger.warning(f"'To' address validation failed for shipment {shipment.id}: {to_result.get('error')}")
                            failed_count += 1
                    
                    # Validate "From" address (optional)
                    if shipment.from_address_line1:
                        logger.info(f"Validating 'From' address for shipment {shipment.id}")
                        from_result = validator.validate_address(
                            address_line1=shipment.from_address_line1,
                            address_line2=shipment.from_address_line2,
                            city=shipment.from_city,
                            state=shipment.from_state,
                            zip_code=shipment.from_zip_code
                        )
                        
                        if from_result['valid']:
                            shipment.from_address_validated = True
                            shipment.from_address_validation_result = from_result
                            logger.info(f"'From' address validated for shipment {shipment.id}")
                    
                    shipment.save()
                    
                except Exception as e:
                    logger.error(f"Error validating addresses for shipment {shipment.id}: {str(e)}")
                    failed_count += 1
            
            logger.info(f"Address validation complete for batch {batch.id}. Validated: {validated_count}, Failed: {failed_count}")
            
            return APIResponse.success(
                message="Address validation complete",
                data={
                    "validated": validated_count,
                    "failed": failed_count
                }
            )
        except ShipmentBatch.DoesNotExist:
            logger.warning(f"Batch not found")
            return APIResponse.not_found("Batch not found")
        except Exception as e:
            logger.error(f"Error validating addresses: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to validate addresses",
                errors=str(e)
            )


class CalculateCostsView(APIView):
    """
    Calculate shipping costs for all shipments in batch
    POST /api/v1/batches/{id}/calculate-costs/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        try:
            batch = ShipmentBatch.objects.get(id=id, user=request.user)
            logger.info(f"User {request.user.username} calculating costs for batch {batch.id}")
            
            shipments = batch.shipments.all()
            from .models import ShippingService
            default_service = ShippingService.objects.filter(
                is_active=True
            ).order_by('base_price').first()
            
            if not default_service:
                logger.error("No active shipping services found")
                return APIResponse.validation_error(
                    message="No shipping services available"
                )
            
            logger.info(f"Using default service: {default_service.name}")
            
            updated_count = 0
            for shipment in shipments:
                if shipment.validation_status == 'valid':
                    cost = default_service.calculate_price(shipment.total_weight_oz)
                    shipment.shipping_service = default_service.name
                    shipment.shipping_cost = cost
                    shipment.save()
                    updated_count += 1
                    
                    logger.debug(f"Shipment {shipment.id}: Service={default_service.name}, Cost=${cost}")
            
            batch.calculate_total_cost()
            
            logger.info(f"Updated shipping costs for {updated_count} shipments in batch {batch.id}. Total: ${batch.total_cost}")
            
            return APIResponse.success(
                message="Shipping costs calculated",
                data={
                    "updated": updated_count,
                    "total_cost": float(batch.total_cost)
                }
            )
        except ShipmentBatch.DoesNotExist:
            logger.warning(f"Batch not found")
            return APIResponse.not_found("Batch not found")
        except Exception as e:
            logger.error(f"Error calculating costs: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to calculate costs",
                errors=str(e)
            )


class ClearBatchView(APIView):
    """
    Delete all shipments in a batch
    DELETE /api/v1/batches/{id}/clear/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, id):
        try:
            batch = ShipmentBatch.objects.get(id=id, user=request.user)
            logger.info(f"User {request.user.username} clearing batch {batch.id}")
            
            count = batch.shipments.count()
            batch.shipments.all().delete()
            batch.total_shipments = 0
            batch.total_cost = 0.00
            batch.save()
            
            logger.info(f"Cleared {count} shipments from batch {batch.id}")
            
            return APIResponse.success(
                message=f"Deleted {count} shipments",
                data={
                    "deleted_count": count
                }
            )
        except ShipmentBatch.DoesNotExist:
            logger.warning(f"Batch not found")
            return APIResponse.not_found("Batch not found")
        except Exception as e:
            logger.error(f"Error clearing batch: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to clear batch",
                errors=str(e)
            )


class ShipmentListView(generics.ListAPIView):
    """
    List shipments (optionally filtered by batch)
    GET /api/v1/shipments/?batch={batch_id}
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShipmentSerializer
    
    def get_queryset(self):
        return Shipment.objects.filter(batch__user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        try:
            batch_id = request.query_params.get('batch')
            
            if batch_id:
                logger.info(f"User {request.user.username} listing shipments for batch {batch_id}")
                queryset = self.get_queryset().filter(batch_id=batch_id)
            else:
                logger.info(f"User {request.user.username} listing all shipments")
                queryset = self.get_queryset()
            
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f"Found {queryset.count()} shipments")
            
            return APIResponse.success(
                message="Shipments retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            logger.error(f"Error listing shipments: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve shipments",
                errors=str(e)
            )


class ShipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update or delete a specific shipment
    GET /api/v1/shipments/{id}/
    PUT/PATCH /api/v1/shipments/{id}/
    DELETE /api/v1/shipments/{id}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return Shipment.objects.filter(batch__user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ShipmentUpdateSerializer
        return ShipmentSerializer
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            logger.info(f"User {request.user.username} retrieving shipment {instance.id}")
            
            serializer = self.get_serializer(instance)
            
            return APIResponse.success(
                message="Shipment retrieved successfully",
                data=serializer.data
            )
        except Shipment.DoesNotExist:
            logger.warning(f"Shipment not found")
            return APIResponse.not_found("Shipment not found")
        except Exception as e:
            logger.error(f"Error retrieving shipment: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve shipment",
                errors=str(e)
            )
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            logger.info(f"User {request.user.username} updating shipment {instance.id}")
            
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
            if serializer.is_valid():
                serializer.save()
                
                logger.info(f"Shipment {instance.id} updated successfully")
                
                return APIResponse.success(
                    message="Shipment updated successfully",
                    data=ShipmentSerializer(instance).data
                )
            else:
                logger.warning(f"Validation failed for shipment update: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Failed to update shipment",
                    errors=serializer.errors
                )
        except Shipment.DoesNotExist:
            logger.warning(f"Shipment not found")
            return APIResponse.not_found("Shipment not found")
        except Exception as e:
            logger.error(f"Error updating shipment: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to update shipment",
                errors=str(e)
            )
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            batch = instance.batch
            shipment_id = instance.id
            
            logger.info(f"User {request.user.username} deleting shipment {shipment_id}")
            
            instance.delete()
            
            # Update batch counts
            batch.total_shipments = batch.shipments.count()
            batch.calculate_total_cost()
            
            logger.info(f"Deleted shipment {shipment_id}. Batch {batch.id} now has {batch.total_shipments} shipments")
            
            return APIResponse.success(
                message="Shipment deleted successfully"
            )
        except Shipment.DoesNotExist:
            logger.warning(f"Shipment not found")
            return APIResponse.not_found("Shipment not found")
        except Exception as e:
            logger.error(f"Error deleting shipment: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to delete shipment",
                errors=str(e)
            )


class BulkDeleteShipmentsView(APIView):
    """
    Delete multiple shipments
    POST /api/v1/shipments/bulk-delete/
    Body: {"shipment_ids": ["uuid1", "uuid2", ...]}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            shipment_ids = request.data.get('shipment_ids', [])
            
            if not shipment_ids:
                logger.warning("No shipment IDs provided for bulk delete")
                return APIResponse.validation_error(
                    message="No shipment IDs provided"
                )
            
            logger.info(f"User {request.user.username} bulk deleting {len(shipment_ids)} shipments")
            
            # Get shipments and verify ownership
            shipments = Shipment.objects.filter(
                id__in=shipment_ids,
                batch__user=request.user
            )
            
            if shipments.count() != len(shipment_ids):
                logger.warning(f"Some shipments not found or not owned by user")
                return APIResponse.not_found(
                    "Some shipments not found or not accessible"
                )
            
            # Get affected batches
            batch_ids = set(shipments.values_list('batch_id', flat=True))
            
            # Delete shipments
            deleted_count = shipments.count()
            shipments.delete()
            
            logger.info(f"Deleted {deleted_count} shipments")
            
            # Update batch counts
            for batch_id in batch_ids:
                try:
                    batch = ShipmentBatch.objects.get(id=batch_id)
                    batch.total_shipments = batch.shipments.count()
                    batch.calculate_total_cost()
                    logger.info(f"Updated batch {batch_id} counts")
                except ShipmentBatch.DoesNotExist:
                    logger.warning(f"Batch {batch_id} not found")
            
            return APIResponse.success(
                message=f"Deleted {deleted_count} shipments",
                data={
                    "deleted_count": deleted_count
                }
            )
        except Exception as e:
            logger.error(f"Error bulk deleting shipments: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to delete shipments",
                errors=str(e)
            )


class BulkUpdateAddressView(APIView):
    """
    Update address for multiple shipments
    POST /api/v1/shipments/bulk-update-address/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = BulkUpdateAddressSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed for bulk address update: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Invalid request data",
                    errors=serializer.errors
                )
            
            data = serializer.validated_data
            shipment_ids = data['shipment_ids']
            address_type = data['address_type']
            
            logger.info(f"User {request.user.username} bulk updating {address_type} address for {len(shipment_ids)} shipments")
            
            # Get shipments and verify ownership
            shipments = Shipment.objects.filter(
                id__in=shipment_ids,
                batch__user=request.user
            )
            
            if shipments.count() != len(shipment_ids):
                logger.warning("Some shipments not found or not owned by user")
                return APIResponse.not_found(
                    "Some shipments not found or not accessible"
                )
            
            # Update shipments
            updated_count = 0
            with transaction.atomic():
                for shipment in shipments:
                    # Build field prefix
                    prefix = f"{address_type}_"
                    
                    # Update fields
                    setattr(shipment, f"{prefix}first_name", data.get('first_name', ''))
                    setattr(shipment, f"{prefix}last_name", data.get('last_name', ''))
                    setattr(shipment, f"{prefix}address_line1", data['address_line1'])
                    setattr(shipment, f"{prefix}address_line2", data.get('address_line2', ''))
                    setattr(shipment, f"{prefix}city", data['city'])
                    setattr(shipment, f"{prefix}state", data['state'])
                    setattr(shipment, f"{prefix}zip_code", data['zip_code'])
                    
                    shipment.save()
                    
                    # Re-validate shipment
                    shipment.validate_shipment()
                    
                    updated_count += 1
                    logger.debug(f"Updated {address_type} address for shipment {shipment.id}")
            
            logger.info(f"Bulk updated {address_type} address for {updated_count} shipments")
            
            return APIResponse.success(
                message=f"Updated {address_type} address for {updated_count} shipments",
                data={
                    "updated_count": updated_count
                }
            )
        except Exception as e:
            logger.error(f"Error bulk updating address: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to update addresses",
                errors=str(e)
            )


class BulkUpdatePackageView(APIView):
    """
    Update package details for multiple shipments
    POST /api/v1/shipments/bulk-update-package/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = BulkUpdatePackageSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed for bulk package update: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Invalid request data",
                    errors=serializer.errors
                )
            
            data = serializer.validated_data
            shipment_ids = data['shipment_ids']
            
            logger.info(f"User {request.user.username} bulk updating package details for {len(shipment_ids)} shipments")
            
            # Get shipments and verify ownership
            shipments = Shipment.objects.filter(
                id__in=shipment_ids,
                batch__user=request.user
            )
            
            if shipments.count() != len(shipment_ids):
                logger.warning("Some shipments not found or not owned by user")
                return APIResponse.not_found(
                    "Some shipments not found or not accessible"
                )
            
            # Update shipments
            updated_count = 0
            with transaction.atomic():
                for shipment in shipments:
                    shipment.length = data['length']
                    shipment.width = data['width']
                    shipment.height = data['height']
                    shipment.weight_lbs = data['weight_lbs']
                    shipment.weight_oz = data['weight_oz']
                    
                    shipment.save()
                    
                    # Re-validate shipment
                    shipment.validate_shipment()
                    
                    updated_count += 1
                    logger.debug(f"Updated package details for shipment {shipment.id}")
            
            logger.info(f"Bulk updated package details for {updated_count} shipments")
            
            return APIResponse.success(
                message=f"Updated package details for {updated_count} shipments",
                data={
                    "updated_count": updated_count
                }
            )
        except Exception as e:
            logger.error(f"Error bulk updating package: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to update package details",
                errors=str(e)
            )


class BulkUpdateShippingServiceView(APIView):
    """
    Update shipping service for multiple shipments
    POST /api/v1/shipments/bulk-update-shipping-service/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        print(request.data)
        try:
            serializer = BulkUpdateShippingServiceSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed for bulk shipping service update: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Invalid request data",
                    errors=serializer.errors
                )
            
            data = serializer.validated_data
            shipment_ids = data['shipment_ids']
            action = data['action']
            
            logger.info(f"User {request.user.username} bulk updating shipping service ({action}) for {len(shipment_ids)} shipments")
            
            # Get shipments and verify ownership
            shipments = Shipment.objects.filter(
                id__in=shipment_ids,
                batch__user=request.user
            )
            
            if shipments.count() != len(shipment_ids):
                logger.warning("Some shipments not found or not owned by user")
                return APIResponse.not_found(
                    "Some shipments not found or not accessible"
                )
            
            # Determine shipping service based on action
            if action == 'cheapest':
                service = ShippingService.objects.filter(is_active=True).order_by('base_price').first()
            elif action == 'priority':
                service = ShippingService.objects.filter(
                    is_active=True,
                    service_type='priority'
                ).first()
            elif action == 'ground':
                service = ShippingService.objects.filter(
                    is_active=True,
                    service_type='ground'
                ).first()
            else:
                logger.error(f"Invalid action: {action}")
                return APIResponse.validation_error(
                    message="Invalid action"
                )
            
            if not service:
                logger.error(f"No shipping service found for action: {action}")
                return APIResponse.not_found(
                    "No shipping service available"
                )
            
            logger.info(f"Selected service: {service.name}")
            
            # Update shipments
            updated_count = 0
            with transaction.atomic():
                for shipment in shipments:
                    cost = service.calculate_price(shipment.total_weight_oz)
                    shipment.shipping_service = service.name
                    shipment.shipping_cost = cost
                    shipment.save()
                    
                    updated_count += 1
                    logger.debug(f"Updated shipping service for shipment {shipment.id}: {service.name} (${cost})")
                
                # Update batch totals
                batch_ids = set(shipments.values_list('batch_id', flat=True))
                for batch_id in batch_ids:
                    try:
                        batch = ShipmentBatch.objects.get(id=batch_id)
                        batch.calculate_total_cost()
                        logger.info(f"Updated batch {batch_id} total cost: ${batch.total_cost}")
                    except ShipmentBatch.DoesNotExist:
                        logger.warning(f"Batch {batch_id} not found")
            
            logger.info(f"Bulk updated shipping service for {updated_count} shipments")
            
            return APIResponse.success(
                message=f"Updated shipping service for {updated_count} shipments",
                data={
                    "updated_count": updated_count,
                    "service": service.name
                }
            )
        except Exception as e:
            logger.error(f"Error bulk updating shipping service: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to update shipping service",
                errors=str(e)
            )

class ShippingServiceListView(generics.ListAPIView):
    """
    List all active shipping services
    GET /api/shipping/services/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShippingServiceSerializer
    
    def get_queryset(self):
        return ShippingService.objects.filter(is_active=True)
    
    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"User {request.user.username} listing shipping services")
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            logger.info(f"Found {queryset.count()} active shipping services")
            
            return APIResponse.success(
                message="Shipping services retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            logger.error(f"Error listing shipping services: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve shipping services",
                errors=str(e)
            )


class CalculatePriceView(APIView):
    """
    Calculate shipping price for given shipment and service
    POST /api/shipping/services/calculate-price/
    Body: {
        "shipment_id": "uuid",
        "service_id": "uuid"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            serializer = CalculateShippingSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed for calculate price: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Invalid request data",
                    errors=serializer.errors
                )
            
            shipment_id = serializer.validated_data['shipment_id']
            service_id = serializer.validated_data['service_id']
            
            logger.info(f"Calculating price for shipment {shipment_id} with service {service_id}")
            
            try:
                shipment = Shipment.objects.get(
                    id=shipment_id,
                    batch__user=request.user
                )
                service = ShippingService.objects.get(id=service_id, is_active=True)
                
                price = service.calculate_price(shipment.total_weight_oz)
                
                logger.info(f"Calculated price: ${price} for shipment {shipment_id}")
                
                return APIResponse.success(
                    message="Price calculated successfully",
                    data={
                        "shipment_id": str(shipment_id),
                        "service_id": str(service_id),
                        "service_name": service.name,
                        "price": float(price),
                        "weight_oz": shipment.total_weight_oz
                    }
                )
                
            except Shipment.DoesNotExist:
                logger.error(f"Shipment {shipment_id} not found or not accessible")
                return APIResponse.not_found("Shipment not found")
            except ShippingService.DoesNotExist:
                logger.error(f"Service {service_id} not found")
                return APIResponse.not_found("Shipping service not found")
                
        except Exception as e:
            logger.error(f"Error calculating price: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to calculate price",
                errors=str(e)
            )


class LabelPurchaseListView(generics.ListAPIView):
    """
    List all label purchases for current user
    GET /api/shipping/purchases/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LabelPurchaseSerializer
    
    def get_queryset(self):
        return LabelPurchase.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        try:
            logger.info(f"User {request.user.username} listing label purchases")
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            logger.info(f"Found {queryset.count()} purchases for user {request.user.username}")
            
            return APIResponse.success(
                message="Purchases retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            logger.error(f"Error listing purchases: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve purchases",
                errors=str(e)
            )


class LabelPurchaseDetailView(generics.RetrieveAPIView):
    """
    Get a specific purchase
    GET /api/shipping/purchases/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LabelPurchaseSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return LabelPurchase.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            logger.info(f"User {request.user.username} retrieving purchase {instance.id}")
            
            serializer = self.get_serializer(instance)
            
            return APIResponse.success(
                message="Purchase retrieved successfully",
                data=serializer.data
            )
        except LabelPurchase.DoesNotExist:
            logger.warning(f"Purchase not found")
            return APIResponse.not_found("Purchase not found")
        except Exception as e:
            logger.error(f"Error retrieving purchase: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to retrieve purchase",
                errors=str(e)
            )


class CreatePurchaseView(APIView):
    """
    Purchase labels for a batch
    POST /api/shipping/purchases/
    Body: {
        "batch_id": "uuid",
        "label_size": "letter" or "4x6",
        "terms_accepted": true
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            print('request.data', request.data)
            serializer = LabelPurchaseCreateSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.warning(f"Validation failed for purchase creation: {serializer.errors}")
                return APIResponse.validation_error(
                    message="Invalid request data",
                    errors=serializer.errors
                )
            
            batch_id = serializer.validated_data['batch_id']
            label_size = serializer.validated_data['label_size']
            terms_accepted = serializer.validated_data['terms_accepted']
            
            logger.info(f"User {request.user.username} purchasing labels for batch {batch_id}")
            
            try:        
                batch = ShipmentBatch.objects.get(id=batch_id, user=request.user)
                
                shipment_count = batch.shipments.count()
                if shipment_count == 0:
                    logger.warning(f"Batch {batch_id} has no shipments")
                    return APIResponse.validation_error(
                        message="Batch has no shipments"
                    )
                
                total_cost = batch.calculate_total_cost()
                
                if request.user.account_balance < total_cost:
                    logger.warning(f"Insufficient balance for user {request.user.username}. Required: ${total_cost}, Available: ${request.user.account_balance}")
                    return APIResponse.validation_error(
                        message="Insufficient account balance",
                        errors={
                            "required": float(total_cost),
                            "available": float(request.user.account_balance)
                        }
                    )
                
                with transaction.atomic():
                    request.user.account_balance -= total_cost
                    request.user.save()
                    
                    logger.info(f"Deducted ${total_cost} from user {request.user.username}. New balance: ${request.user.account_balance}")
                    
                    purchase = LabelPurchase.objects.create(
                        batch=batch,
                        user=request.user,
                        label_size=label_size,
                        total_amount=total_cost,
                        total_labels=shipment_count,
                        terms_accepted=terms_accepted
                    )
                    
                    batch.status = 'purchased'
                    batch.purchased_at = timezone.now()
                    batch.save()
                    
                    logger.info(f"Created purchase {purchase.id} for batch {batch_id}. Total: ${total_cost}, Labels: {shipment_count}")
                
                return APIResponse.created(
                    message="Labels purchased successfully",
                    data=LabelPurchaseSerializer(purchase).data
                )
                
            except ShipmentBatch.DoesNotExist:
                logger.error(f"Batch {batch_id} not found or not accessible")
                return APIResponse.not_found("Batch not found")
                
        except Exception as e:
            logger.error(f"Error processing purchase: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to process purchase",
                errors=str(e)
            )


from django.http import FileResponse
import os
from pathlib import Path

class DownloadLabelsView(APIView):
    """
    Download label file (PSD or other formats)
    GET /api/shipping/purchases/{id}/download/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id, format=None):
        try:
            purchase = LabelPurchase.objects.get(id=id, user=request.user)
            logger.info(f"User {request.user.username} downloading labels for purchase {purchase.id}")
            
            # Check if format is specified (e.g., ?format=psd)
            download_format = request.GET.get('format', 'psd').lower()
            
            # Determine file path based on format
            if download_format == 'psd':
                # Assuming you have PSD files stored
                file_path = purchase.psdlabel_file.path 
                    
                content_type = 'image/vnd.adobe.photoshop'
                filename = f"labels_{purchase.batch.id}.psd"
                
            elif download_format == 'pdf':
                # For PDF files
                file_path = purchase.pdf_file.path
                content_type = 'application/pdf'
                filename = f"labels_{purchase.batch.id}.pdf"
            else:
                return APIResponse.error("Unsupported format")
            
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return APIResponse.not_found("File not found")
            
            # Return file as download
            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type,
                as_attachment=True,
                filename=filename
            )
            
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['X-File-Name'] = filename
            
            return response
            
        except LabelPurchase.DoesNotExist:
            logger.warning(f"Purchase not found")
            return APIResponse.not_found("Purchase not found")
        except Exception as e:
            logger.error(f"Error downloading labels: {str(e)}", exc_info=True)
            return APIResponse.error(
                message="Failed to download labels",
                errors=str(e)
            )