"""
Utility functions for CSV parsing and address validation
"""
import csv
import io
import logging
import requests
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Parser for shipping CSV files
    Handles the 2-header-row format specified in the PRD
    """
    
    def __init__(self, csv_content: str):
        """
        Initialize parser with CSV content
        
        Args:
            csv_content: String content of CSV file
        """
        self.csv_content = csv_content
        self.reader = csv.reader(io.StringIO(csv_content))
    
    def parse(self) -> List[Dict]:
        """
        Parse CSV and return list of shipment data dictionaries
        
        Returns:
            List of dictionaries containing shipment data
        """
        logger.info("Starting CSV parsing")
        
        try:
            # Skip first two header rows
            next(self.reader)  # Skip row 1
            next(self.reader)  # Skip row 2
            
            shipments = []
            row_number = 3  # Start from data row (row 3 in file)
            
            for row in self.reader:
                if not row or len(row) < 14:
                    logger.warning(f"Skipping incomplete row {row_number}")
                    row_number += 1
                    continue
                
                try:
                    shipment_data = self._parse_row(row, row_number)
                    shipments.append(shipment_data)
                    logger.debug(f"Parsed row {row_number}: Order #{shipment_data.get('order_number', 'N/A')}")
                except Exception as e:
                    logger.error(f"Error parsing row {row_number}: {str(e)}")
                
                row_number += 1
            
            logger.info(f"Successfully parsed {len(shipments)} shipments from CSV")
            return shipments
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}", exc_info=True)
            raise
    
    def _parse_row(self, row: List[str], row_number: int) -> Dict:
        """
        Parse a single CSV row into shipment data
        
        Args:
            row: List of cell values
            row_number: Row number in CSV
        
        Returns:
            Dictionary of shipment data
        """
        # Helper function to safely get value
        def get_value(index: int, default: str = '') -> str:
            try:
                value = row[index].strip() if index < len(row) else default
                return value if value else default
            except (IndexError, AttributeError):
                return default
        
        # Helper function to parse numeric value
        def get_numeric(index: int, default: int = 0) -> int:
            try:
                value = get_value(index)
                return int(float(value)) if value else default
            except (ValueError, TypeError):
                return default
        
        # Helper function to parse decimal value
        def get_decimal(index: int, default: float = 0.0) -> float:
            try:
                value = get_value(index)
                return float(value) if value else default
            except (ValueError, TypeError):
                return default
        
        return {
            'row_number': row_number,
            # Ship From Address (indices 0-6)
            'from_first_name': get_value(0),
            'from_last_name': get_value(1),
            'from_address_line1': get_value(2),
            'from_address_line2': get_value(3),
            'from_city': get_value(4),
            'from_zip_code': get_value(5),
            'from_state': get_value(6).upper() if get_value(6) else '',
            # Ship To Address (indices 7-13)
            'to_first_name': get_value(7),
            'to_last_name': get_value(8),
            'to_address_line1': get_value(9),
            'to_address_line2': get_value(10),
            'to_city': get_value(11),
            'to_zip_code': get_value(12),
            'to_state': get_value(13).upper() if get_value(13) else '',
            # Package Details (indices 14-18)
            'weight_lbs': get_numeric(14, 0),
            'weight_oz': get_numeric(15, 0),
            'length': get_decimal(16, 0.0),
            'width': get_decimal(17, 0.0),
            'height': get_decimal(18, 0.0),
            # Contact & Reference (indices 19-22)
            'phone_1': get_value(19),
            'phone_2': get_value(20),
            'order_number': get_value(21),
            'item_sku': get_value(22)
        }


class AddressValidator:
    """
    Address validation using multiple APIs with fallback support
    Priority: Smarty (free tier) → Google → USPS
    """
    
    def __init__(self):
        """Initialize validator with API configurations"""
        # Get API keys from settings
        self.smarty_auth_id = getattr(settings, 'SMARTY_AUTH_ID', None)
        self.smarty_auth_token = getattr(settings, 'SMARTY_AUTH_TOKEN', None)
        self.google_api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        self.usps_user_id = getattr(settings, 'USPS_USER_ID', None)
    
    def validate_address(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        address_line2: str = ''
    ) -> Dict:
        """
        Validate an address using available APIs with fallback
        
        Args:
            address_line1: Primary address line
            city: City name
            state: State code (2 letters)
            zip_code: ZIP code
            address_line2: Secondary address line (optional)
        
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'normalized_address': dict (if valid),
                'service': str (which service was used),
                'error': str (if invalid)
            }
        """
        logger.info(f"Validating address: {address_line1}, {city}, {state} {zip_code}")
        
        if self.smarty_auth_id and self.smarty_auth_token:
            result = self._validate_with_smarty(
                address_line1, city, state, zip_code, address_line2
            )
            
            if result['valid']:
                logger.info("Address validated with Smarty")
                return result
            
            logger.warning(f"Smarty validation failed: {result.get('error', 'Unknown error')}")
        else:
            logger.warning("Smarty API credentials not configured")
        
        if self.google_api_key:
            logger.info("Trying Google Address Validation")
            result = self._validate_with_google(
                address_line1, city, state, zip_code, address_line2
            )
            
            if result['valid']:
                logger.info("Address validated with Google")
                return result
            
            logger.warning(f"Google validation failed: {result.get('error', 'Unknown error')}")
        else:
            logger.warning("Google API key not configured")
        
        if self.usps_user_id:
            logger.info("Trying USPS Address Validation")
            result = self._validate_with_usps(
                address_line1, city, state, zip_code, address_line2
            )
            
            if result['valid']:
                logger.info("Address validated with USPS")
                return result
            
            logger.warning(f"USPS validation failed: {result.get('error', 'Unknown error')}")
        else:
            logger.warning("USPS User ID not configured")
        
        logger.error("All address validation services failed or not configured")
        
        return self._basic_validation(address_line1, city, state, zip_code, address_line2)
    
    def _validate_with_smarty(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        address_line2: str = ''
    ) -> Dict:
        """
        Validate address using Smarty (SmartyStreets) US Street API
        
        API Docs: https://www.smarty.com/docs/cloud/us-street-api
        """
        try:
            logger.info("Attempting Smarty validation")
            
            url = "https://us-street.api.smarty.com/street-address"
            
            params = {
                'auth-id': self.smarty_auth_id,
                'auth-token': self.smarty_auth_token,
                'street': address_line1,
                'street2': address_line2,
                'city': city,
                'state': state,
                'zipcode': zip_code,
                'match': 'invalid',  # Return only valid addresses
            }
            
            logger.debug(f"Smarty API request: {url}")
            response = requests.get(url, params=params, timeout=10)
            
            logger.debug(f"Smarty response status: {response.status_code}")
            
            if response.status_code == 200:
                results = response.json()
                
                if results and len(results) > 0:
                    result = results[0]
                    components = result.get('components', {})
                    metadata = result.get('metadata', {})
                    analysis = result.get('analysis', {})
                    
                    dpv_match_code = analysis.get('dpv_match_code', '')
                    
                    logger.info(f"Smarty validation result: DPV={dpv_match_code}")
                    
                    if dpv_match_code in ['Y', 'S', 'D']:
                        normalized = {
                            'address_line1': result.get('delivery_line_1', address_line1),
                            'address_line2': result.get('delivery_line_2', address_line2),
                            'city': components.get('city_name', city),
                            'state': components.get('state_abbreviation', state),
                            'zip_code': components.get('zipcode', zip_code) + '-' + components.get('plus4_code', '0000'),
                        }
                        
                        return {
                            'valid': True,
                            'normalized_address': normalized,
                            'service': 'smarty',
                            'confidence': 'high' if dpv_match_code == 'Y' else 'medium',
                            'metadata': {
                                'rdi': metadata.get('rdi', ''),
                                'precision': metadata.get('precision', ''),
                            }
                        }
                    else:
                        return {
                            'valid': False,
                            'error': f'Address not deliverable (DPV: {dpv_match_code})',
                            'service': 'smarty'
                        }
                else:
                    return {
                        'valid': False,
                        'error': 'No matching addresses found',
                        'service': 'smarty'
                    }
            
            elif response.status_code == 401:
                logger.error("Smarty authentication failed - check credentials")
                return {
                    'valid': False,
                    'error': 'Authentication failed',
                    'service': 'smarty'
                }
            
            elif response.status_code == 402:
                logger.error("Smarty payment required - free tier limit reached")
                return {
                    'valid': False,
                    'error': 'Payment required (free tier limit)',
                    'service': 'smarty'
                }
            
            else:
                logger.error(f"Smarty API error: {response.status_code} - {response.text}")
                return {
                    'valid': False,
                    'error': f'API error: {response.status_code}',
                    'service': 'smarty'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Smarty API timeout")
            return {
                'valid': False,
                'error': 'Request timeout',
                'service': 'smarty'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Smarty API request error: {str(e)}")
            return {
                'valid': False,
                'error': f'Request error: {str(e)}',
                'service': 'smarty'
            }
        except Exception as e:
            logger.error(f"Smarty validation error: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': str(e),
                'service': 'smarty'
            }
    
    def _validate_with_google(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        address_line2: str = ''
    ) -> Dict:
        """
        Validate address using Google Address Validation API
        
        API Docs: https://developers.google.com/maps/documentation/address-validation
        """
        try:
            logger.info("Attempting Google validation")
            
            url = "https://addressvalidation.googleapis.com/v1:validateAddress"
            
            address_parts = [address_line1]
            if address_line2:
                address_parts.append(address_line2)
            address_parts.extend([city, state, zip_code])
            full_address = ', '.join(filter(None, address_parts))
            
            payload = {
                'address': {
                    'regionCode': 'US',
                    'addressLines': [full_address]
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
            }
            params = {
                'key': self.google_api_key
            }
            
            logger.debug(f"Google API request: {url}")
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                params=params,
                timeout=10
            )
            
            logger.debug(f"Google response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                verdict = result.get('result', {}).get('verdict', {})
                
                validation_granularity = verdict.get('validationGranularity', '')
                
                logger.info(f"Google validation result: {validation_granularity}")
                
                if validation_granularity in ['PREMISE', 'SUB_PREMISE']:
                    formatted_address = result.get('result', {}).get('address', {})
                    postal_address = formatted_address.get('postalAddress', {})
                    
                    normalized = {
                        'address_line1': postal_address.get('addressLines', [address_line1])[0],
                        'address_line2': address_line2,
                        'city': postal_address.get('locality', city),
                        'state': postal_address.get('administrativeArea', state),
                        'zip_code': postal_address.get('postalCode', zip_code),
                    }
                    
                    return {
                        'valid': True,
                        'normalized_address': normalized,
                        'service': 'google',
                        'confidence': 'high' if validation_granularity == 'PREMISE' else 'medium'
                    }
                else:
                    return {
                        'valid': False,
                        'error': f'Insufficient validation granularity: {validation_granularity}',
                        'service': 'google'
                    }
            else:
                logger.error(f"Google API error: {response.status_code} - {response.text}")
                return {
                    'valid': False,
                    'error': f'API error: {response.status_code}',
                    'service': 'google'
                }
                
        except Exception as e:
            logger.error(f"Google validation error: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': str(e),
                'service': 'google'
            }
    
    def _validate_with_usps(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        address_line2: str = ''
    ) -> Dict:
        """
        Validate address using USPS Address Validation API
        
        API Docs: https://www.usps.com/business/web-tools-apis/
        """
        try:
            logger.info("Attempting USPS validation")
            
            url = "https://secure.shippingapis.com/ShippingAPI.dll"
            
            xml_request = f"""
            <AddressValidateRequest USERID="{self.usps_user_id}">
                <Address>
                    <Address1>{address_line2}</Address1>
                    <Address2>{address_line1}</Address2>
                    <City>{city}</City>
                    <State>{state}</State>
                    <Zip5>{zip_code[:5]}</Zip5>
                    <Zip4></Zip4>
                </Address>
            </AddressValidateRequest>
            """
            
            params = {
                'API': 'Verify',
                'XML': xml_request
            }
            
            logger.debug(f"USPS API request: {url}")
            response = requests.get(url, params=params, timeout=10)
            
            logger.debug(f"USPS response status: {response.status_code}")
            
            if response.status_code == 200:
                if '<Error>' in response.text:
                    logger.warning("USPS returned error in response")
                    return {
                        'valid': False,
                        'error': 'USPS validation error',
                        'service': 'usps'
                    }
                
                return {
                    'valid': True,
                    'normalized_address': {
                        'address_line1': address_line1,
                        'address_line2': address_line2,
                        'city': city,
                        'state': state,
                        'zip_code': zip_code,
                    },
                    'service': 'usps',
                    'confidence': 'medium'
                }
            else:
                return {
                    'valid': False,
                    'error': f'API error: {response.status_code}',
                    'service': 'usps'
                }
                
        except Exception as e:
            logger.error(f"USPS validation error: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': str(e),
                'service': 'usps'
            }
    
    def _basic_validation(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        address_line2: str = ''
    ) -> Dict:
        """
        Fallback basic validation when all APIs fail
        Just checks if required fields are present
        """
        logger.info("Using basic validation (all APIs unavailable)")
        
        if not all([address_line1, city, state, zip_code]):
            return {
                'valid': False,
                'error': 'Missing required address fields',
                'service': 'basic'
            }
        
        if len(state) != 2:
            return {
                'valid': False,
                'error': 'Invalid state code',
                'service': 'basic'
            }
        
        zip_clean = zip_code.replace('-', '')
        if not (len(zip_clean) == 5 or len(zip_clean) == 9):
            return {
                'valid': False,
                'error': 'Invalid ZIP code format',
                'service': 'basic'
            }
        
        logger.warning("Address validated with basic rules only - API validation recommended")
        
        return {
            'valid': True,
            'normalized_address': {
                'address_line1': address_line1.title(),
                'address_line2': address_line2,
                'city': city.title(),
                'state': state.upper(),
                'zip_code': zip_code,
            },
            'service': 'basic',
            'confidence': 'low',
            'warning': 'Validated with basic rules only - full API validation unavailable'
        }