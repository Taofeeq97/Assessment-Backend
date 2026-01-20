from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.db import models
from django.core.paginator import Paginator, EmptyPage
from account.models import SavedAddress, SavedPackage
from account.serializers import (
    UserSerializer,
    UserProfileSerializer,
    SavedAddressSerializer,
    SavedAddressCreateSerializer,
    SavedPackageSerializer,
    SavedPackageCreateSerializer,
    LoginSerializer
)
from base.response import APIResponse
from rest_framework_simplejwt.tokens import RefreshToken
User = get_user_model()



class LoginView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            print('serializer', serializer)
            if serializer.is_valid():
                print('serializer is valid')
                user = serializer.validated_data['user']
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                print('refresh_token', refresh_token)
                user_serializer = UserSerializer(user, context={'request': request})
                print('user_serializer', user_serializer)

                token_data = {
                    'access': access_token,
                    'refresh': refresh_token,
                    'user': user_serializer.data
                }
                print('token_data', token_data)
                return APIResponse.success(
                    message="Login successful",
                    data=token_data
                )
            else:
                print('serializer is not valid')
                print('serializer errors', serializer.errors)
                return APIResponse.validation_error(
                    message="Login failed",
                    errors=serializer.errors
                )

        except Exception as e:
            print('error', e)
            return APIResponse.error(
                message="Login failed",
                errors=str(e)
            )


class UserProfileView(generics.RetrieveAPIView):
    """
    Get current user's profile
    GET /api/v1/me/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(request.user)
            
            return APIResponse.success(
                message="User profile retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            return APIResponse.error(
                message="Failed to retrieve user profile",
                errors=str(e)
            )


class AddBalanceView(APIView):
    """
    Add balance to user account (for demo purposes)
    POST /api/v1/add-balance/
    Body: {"amount": 100.00}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            print('request.data', request.data)
            amount = request.data.get('amount', 0)
            
            try:
                amount = float(amount)
                if amount <= 0:
                    print('amount is less than 0')
                    return APIResponse.validation_error(
                        message="Amount must be greater than 0"
                    )
                user_balance = request.user.account_balance
                user_balance = float(user_balance) + float(amount)
                request.user.account_balance = user_balance
                request.user.save()
                print('request.user.account_balance', request.user.account_balance) 
                return APIResponse.success(
                    message=f"Successfully added ${amount} to your account",
                    data={
                        "new_balance": float(request.user.account_balance)
                    }
                )
            except (ValueError, TypeError) as e:
                print('error', e)
                return APIResponse.validation_error(
                    message="Invalid amount"
                )
        except Exception as e:
            print('error', e)
            return APIResponse.error(
                message="Failed to add balance",
                errors=str(e)
            )


class SavedAddressListCreateView(generics.ListCreateAPIView):
    """
    List all saved addresses or create a new one
    GET /api/v1/saved-addresses/
    POST /api/v1/saved-addresses/
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedAddress.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SavedAddressCreateSerializer
        return SavedAddressSerializer
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return APIResponse.success(
                message="Saved addresses retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            return APIResponse.error(
                message="Failed to retrieve saved addresses",
                errors=str(e)
            )
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                address = SavedAddress.objects.create(
                    user=request.user,
                    **serializer.validated_data
                )
                
                return APIResponse.created(
                    message="Saved address created successfully",
                    data=SavedAddressSerializer(address).data
                )
            else:
                return APIResponse.validation_error(
                    message="Failed to create saved address",
                    errors=serializer.errors
                )
        except Exception as e:
            return APIResponse.error(
                message="Failed to create saved address",
                errors=str(e)
            )


class SavedAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a saved address
    GET /api/v1/saved-addresses/{id}/
    PUT/PATCH /api/v1/saved-addresses/{id}/
    DELETE /api/v1/saved-addresses/{id}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return SavedAddress.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SavedAddressCreateSerializer
        return SavedAddressSerializer
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            serializer = self.get_serializer(instance)
            
            return APIResponse.success(
                message="Saved address retrieved successfully",
                data=serializer.data
            )
        except SavedAddress.DoesNotExist:
            return APIResponse.not_found("Saved address not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to retrieve saved address",
                errors=str(e)
            )
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            
            serializer = SavedAddressCreateSerializer(
                instance,
                data=request.data,
                partial=partial
            )
            
            if serializer.is_valid():
                serializer.save()
                
                return APIResponse.success(
                    message="Saved address updated successfully",
                    data=SavedAddressSerializer(instance).data
                )
            else:
                return APIResponse.validation_error(
                    message="Failed to update saved address",
                    errors=serializer.errors
                )
        except SavedAddress.DoesNotExist:
            return APIResponse.not_found("Saved address not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to update saved address",
                errors=str(e)
            )
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            address_id = instance.id            
            instance.delete()
            
            return APIResponse.success(
                message="Saved address deleted successfully"
            )
        except SavedAddress.DoesNotExist:
            return APIResponse.not_found("Saved address not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to delete saved address",
                errors=str(e)
            )


class SetDefaultAddressView(APIView):
    """
    Set an address as default
    POST /api/v1/saved-addresses/{id}/set-default/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            address = SavedAddress.objects.get(id=id, user=request.user)
            
            SavedAddress.objects.filter(
                user=request.user,
                is_default=True
            ).exclude(id=address.id).update(is_default=False)
            
            address.is_default = True
            address.save()
            return APIResponse.success(
                message="Default address set successfully",
                data=SavedAddressSerializer(address).data
            )
        except SavedAddress.DoesNotExist:
            return APIResponse.not_found("Saved address not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to set default address",
                errors=str(e)
            )


class SavedPackageListCreateView(generics.ListCreateAPIView):
    """
    List all saved packages or create a new one
    GET /api/v1/saved-packages/
    POST /api/v1/saved-packages/
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedPackage.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SavedPackageCreateSerializer
        return SavedPackageSerializer
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            return APIResponse.success(
                message="Saved packages retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            return APIResponse.error(
                message="Failed to retrieve saved packages",
                errors=str(e)
            )
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                package = SavedPackage.objects.create(
                    user=request.user,
                    **serializer.validated_data
                )
                
                return APIResponse.created(
                    message="Saved package created successfully",
                    data=SavedPackageSerializer(package).data
                )
            else:
                return APIResponse.validation_error(
                    message="Failed to create saved package",
                    errors=serializer.errors
                )
        except Exception as e:
            return APIResponse.error(
                message="Failed to create saved package",
                errors=str(e)
            )


class SavedPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a saved package
    GET /api/v1/saved-packages/{id}/
    PUT/PATCH /api/v1/saved-packages/{id}/
    DELETE /api/v1/saved-packages/{id}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        return SavedPackage.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SavedPackageCreateSerializer
        return SavedPackageSerializer
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            serializer = self.get_serializer(instance)
            
            return APIResponse.success(
                message="Saved package retrieved successfully",
                data=serializer.data
            )
        except SavedPackage.DoesNotExist:
            return APIResponse.not_found("Saved package not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to retrieve saved package",
                errors=str(e)
            )
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            

            serializer = SavedPackageCreateSerializer(
                instance,
                data=request.data,
                partial=partial
            )
            
            if serializer.is_valid():
                serializer.save()
                
                return APIResponse.success(
                    message="Saved package updated successfully",
                    data=SavedPackageSerializer(instance).data
                )
            else:
                return APIResponse.validation_error(
                    message="Failed to update saved package",
                    errors=serializer.errors
                )
        except SavedPackage.DoesNotExist:
            return APIResponse.not_found("Saved package not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to update saved package",
                errors=str(e)
            )
    
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            package_id = instance.id
            
            instance.delete()
            
            return APIResponse.success(
                message="Saved package deleted successfully"
            )
        except SavedPackage.DoesNotExist:
            return APIResponse.not_found("Saved package not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to delete saved package",
                errors=str(e)
            )


class SetDefaultPackageView(APIView):
    """
    Set a package as default
    POST /api/v1/saved-packages/{id}/set-default/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            package = SavedPackage.objects.get(id=id, user=request.user)
            
            SavedPackage.objects.filter(
                user=request.user,
                is_default=True
            ).exclude(id=package.id).update(is_default=False)
            
            package.is_default = True
            package.save()
            
            return APIResponse.success(
                message="Default package set successfully",
                data=SavedPackageSerializer(package).data
            )
        except SavedPackage.DoesNotExist:
            return APIResponse.not_found("Saved package not found")
        except Exception as e:
            return APIResponse.error(
                message="Failed to set default package",
                errors=str(e)
            )