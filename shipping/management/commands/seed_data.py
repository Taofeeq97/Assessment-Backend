from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from account.models import SavedAddress, SavedPackage
from shipping.models import ShippingService
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds database with initial data for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        self.create_demo_user()
        self.create_saved_addresses()   
        self.create_saved_packages()
        self.create_shipping_services()        
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))
    
    def create_demo_user(self):
        """Create a demo user for testing"""
        username = 'demo'
        email = 'demo@example.com'
        password = 'demo123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists'))
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Demo',
                last_name='User',
                account_balance=Decimal('1000.00')
            )
            self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
        
        return user
    
    def create_saved_addresses(self):
        """Create sample saved addresses"""
        user = User.objects.get(username='demo')
        
        addresses = [
            {
                'name': 'Print TTS - San Dimas',
                'first_name': 'Print',
                'last_name': 'TTS',
                'address_line1': '502 W Arrow Hwy',
                'address_line2': 'STE P',
                'city': 'San Dimas',
                'state': 'CA',
                'zip_code': '91773',
                'phone': '(626) 555-0100',
                'is_default': True
            },
            {
                'name': 'Print TTS - Claremont',
                'first_name': 'Print',
                'last_name': 'TTS',
                'address_line1': '500 W Foothill Blvd',
                'address_line2': 'STE P',
                'city': 'Claremont',
                'state': 'CA',
                'zip_code': '91711',
                'phone': '(909) 555-0200',
                'is_default': False
            },
            {
                'name': 'Print TTS - Ontario',
                'first_name': 'Print',
                'last_name': 'TTS',
                'address_line1': '1170 Grove Ave',
                'address_line2': '',
                'city': 'Ontario',
                'state': 'CA',
                'zip_code': '91764',
                'phone': '(909) 555-0300',
                'is_default': False
            }
        ]
        
        created_count = 0
        for addr_data in addresses:
            addr, created = SavedAddress.objects.get_or_create(
                user=user,
                name=addr_data['name'],
                defaults=addr_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created address: {addr.name}')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} saved addresses'))
        else:
            self.stdout.write(self.style.WARNING('Saved addresses already exist'))
    
    def create_saved_packages(self):
        """Create sample saved packages"""
        user = User.objects.get(username='demo')
        
        packages = [
            {
                'name': 'Light Package',
                'length': Decimal('6.00'),
                'width': Decimal('6.00'),
                'height': Decimal('6.00'),
                'weight_lbs': 1,
                'weight_oz': 0,
                'is_default': True
            },
            {
                'name': '8 Oz Item',
                'length': Decimal('4.00'),
                'width': Decimal('4.00'),
                'height': Decimal('4.00'),
                'weight_lbs': 0,
                'weight_oz': 8,
                'is_default': False
            },
            {
                'name': 'Standard Box',
                'length': Decimal('12.00'),
                'width': Decimal('12.00'),
                'height': Decimal('12.00'),
                'weight_lbs': 2,
                'weight_oz': 0,
                'is_default': False
            }
        ]
        
        created_count = 0
        for pkg_data in packages:
            pkg, created = SavedPackage.objects.get_or_create(
                user=user,
                name=pkg_data['name'],
                defaults=pkg_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created package: {pkg.name}')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} saved packages'))
        else:
            self.stdout.write(self.style.WARNING('Saved packages already exist'))
    
    def create_shipping_services(self):
        """Create shipping service options"""
        services = [
            {
                'name': 'Priority Mail',
                'service_type': 'priority',
                'description': 'Fast delivery (1-3 business days)',
                'base_price': Decimal('5.00'),
                'per_oz_rate': Decimal('0.10'),
                'delivery_days_min': 1,
                'delivery_days_max': 3,
                'is_active': True
            },
            {
                'name': 'Ground Shipping',
                'service_type': 'ground',
                'description': 'Economy delivery (3-7 business days)',
                'base_price': Decimal('2.50'),
                'per_oz_rate': Decimal('0.05'),
                'delivery_days_min': 3,
                'delivery_days_max': 7,
                'is_active': True
            },
            {
                'name': 'Express Shipping',
                'service_type': 'express',
                'description': 'Next day delivery',
                'base_price': Decimal('15.00'),
                'per_oz_rate': Decimal('0.20'),
                'delivery_days_min': 1,
                'delivery_days_max': 1,
                'is_active': True
            }
        ]
        
        created_count = 0
        for svc_data in services:
            svc, created = ShippingService.objects.get_or_create(
                name=svc_data['name'],
                defaults=svc_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created service: {svc.name}')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Created {created_count} shipping services'))
        else:
            self.stdout.write(self.style.WARNING('Shipping services already exist'))