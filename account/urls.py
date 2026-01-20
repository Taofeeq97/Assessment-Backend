from django.urls import path
from account.views import (
    LoginView,
    UserProfileView,
    AddBalanceView,
    SavedAddressListCreateView,
    SavedAddressDetailView,
    SetDefaultAddressView,
    SavedPackageListCreateView,
    SavedPackageDetailView,
    SetDefaultPackageView
)

app_name = 'account'

urlpatterns = [
    # User endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserProfileView.as_view(), name='user-profile'),
    path('add-balance/', AddBalanceView.as_view(), name='add-balance'),
    
    # Saved Addresses endpoints
    path('saved-addresses/', SavedAddressListCreateView.as_view(), name='saved-address-list-create'),
    path('saved-addresses/<uuid:id>/', SavedAddressDetailView.as_view(), name='saved-address-detail'),
    path('saved-addresses/<uuid:id>/set-default/', SetDefaultAddressView.as_view(), name='saved-address-set-default'),
    
    # Saved Packages endpoints
    path('saved-packages/', SavedPackageListCreateView.as_view(), name='saved-package-list-create'),
    path('saved-packages/<uuid:id>/', SavedPackageDetailView.as_view(), name='saved-package-detail'),
    path('saved-packages/<uuid:id>/set-default/', SetDefaultPackageView.as_view(), name='saved-package-set-default'),
]