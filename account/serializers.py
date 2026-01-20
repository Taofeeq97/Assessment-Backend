from rest_framework import serializers
from django.contrib.auth import get_user_model
from account.models import SavedAddress, SavedPackage
from django.contrib.auth import authenticate

User = get_user_model()



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = User.objects.get(email=email)
            if not user:
                raise serializers.ValidationError("Invalid email or password.")
            if not user.check_password(password):
                raise serializers.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include email and password.")

            

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'account_balance',
        ]
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with minimal info"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'full_name',
            'account_balance'
        ]
        read_only_fields = ['id']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class SavedAddressSerializer(serializers.ModelSerializer):
    """Serializer for SavedAddress model"""
    formatted_address = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedAddress
        fields = [
            'id',
            'name',
            'first_name',
            'last_name',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'zip_code',
            'phone',
            'is_default',
            'formatted_address',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_formatted_address(self, obj):
        """Return formatted address string"""
        name = f"{obj.first_name} {obj.last_name}".strip()
        address2 = f", {obj.address_line2}" if obj.address_line2 else ""
        return f"{name}\n{obj.address_line1}{address2}\n{obj.city}, {obj.state} {obj.zip_code}"
    
    def create(self, validated_data):
        """Create address with user from context"""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class SavedAddressCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved addresses"""
    
    class Meta:
        model = SavedAddress
        fields = [
            'name',
            'first_name',
            'last_name',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'zip_code',
            'phone',
            'is_default'
        ]
    
    def validate_state(self, value):
        """Validate state is a valid 2-letter code"""
        if len(value) != 2:
            raise serializers.ValidationError("State must be a 2-letter code")
        return value.upper()


class SavedPackageSerializer(serializers.ModelSerializer):
    """Serializer for SavedPackage model"""
    dimensions_formatted = serializers.SerializerMethodField()
    weight_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedPackage
        fields = [
            'id',
            'name',
            'length',
            'width',
            'height',
            'weight_lbs',
            'weight_oz',
            'is_default',
            'dimensions_formatted',
            'weight_formatted',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_dimensions_formatted(self, obj):
        """Return formatted dimensions"""
        return f"{obj.length}×{obj.width}×{obj.height} inches"
    
    def get_weight_formatted(self, obj):
        """Return formatted weight"""
        return f"{obj.weight_lbs} lb {obj.weight_oz} oz"
    
    def create(self, validated_data):
        """Create package with user from context"""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class SavedPackageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved packages"""
    
    class Meta:
        model = SavedPackage
        fields = [
            'name',
            'length',
            'width',
            'height',
            'weight_lbs',
            'weight_oz',
            'is_default'
        ]
    
    def validate(self, data):
        """Validate package dimensions and weight"""
        if data.get('length', 0) <= 0:
            raise serializers.ValidationError({"length": "Length must be greater than 0"})
        if data.get('width', 0) <= 0:
            raise serializers.ValidationError({"width": "Width must be greater than 0"})
        if data.get('height', 0) <= 0:
            raise serializers.ValidationError({"height": "Height must be greater than 0"})
        
        weight_lbs = data.get('weight_lbs', 0)
        weight_oz = data.get('weight_oz', 0)
        if weight_lbs == 0 and weight_oz == 0:
            raise serializers.ValidationError(
                {"weight": "Package must have a weight greater than 0"}
            )
        
        return data