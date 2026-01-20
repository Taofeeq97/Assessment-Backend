from django.urls import path
from shipping.views import (
    # Batch views
    ShipmentBatchListView,
    ShipmentBatchDetailView,
    UploadCSVView,
    ValidateAddressesView,
    CalculateCostsView,
    ClearBatchView,
    # Shipment views
    ShipmentListView,
    ShipmentDetailView,
    BulkDeleteShipmentsView,
    BulkUpdateAddressView,
    BulkUpdatePackageView,
    BulkUpdateShippingServiceView,
    # Service views
    ShippingServiceListView,
    CalculatePriceView,
    # Purchase views
    LabelPurchaseListView,
    LabelPurchaseDetailView,
    CreatePurchaseView,
    DownloadLabelsView
)

app_name = 'shipping'

urlpatterns = [
    # Batch endpoints
    path('batches/', ShipmentBatchListView.as_view(), name='batch-list'),
    path('batches/<int:id>/', ShipmentBatchDetailView.as_view(), name='batch-detail'),
    path('batches/upload-csv/', UploadCSVView.as_view(), name='batch-upload-csv'),
    path('batches/<int:id>/validate-addresses/', ValidateAddressesView.as_view(), name='batch-validate-addresses'),
    path('batches/<int:id>/calculate-costs/', CalculateCostsView.as_view(), name='batch-calculate-costs'),
    path('batches/<int:id>/clear/', ClearBatchView.as_view(), name='batch-clear'),
    
    # Shipment endpoints
    path('shipments/', ShipmentListView.as_view(), name='shipment-list'),
    path('shipments/<int:id>/', ShipmentDetailView.as_view(), name='shipment-detail'),
    path('shipments/bulk-delete/', BulkDeleteShipmentsView.as_view(), name='shipment-bulk-delete'),
    path('shipments/bulk-update-address/', BulkUpdateAddressView.as_view(), name='shipment-bulk-update-address'),
    path('shipments/bulk-update-package/', BulkUpdatePackageView.as_view(), name='shipment-bulk-update-package'),
    path('shipments/bulk-update-shipping-service/', BulkUpdateShippingServiceView.as_view(), name='shipment-bulk-update-service'),
    
    # Shipping Service endpoints
    path('services/', ShippingServiceListView.as_view(), name='service-list'),
    path('services/calculate-price/', CalculatePriceView.as_view(), name='service-calculate-price'),
    
    # Purchase endpoints
    path('purchases/', CreatePurchaseView.as_view(), name='purchase-create'),  # POST
    path('purchases/list/', LabelPurchaseListView.as_view(), name='purchase-list'),  # GET
    path('purchases/<int:id>/', LabelPurchaseDetailView.as_view(), name='purchase-detail'),
    path('purchases/<int:id>/download/', DownloadLabelsView.as_view(), name='purchase-download'),
]