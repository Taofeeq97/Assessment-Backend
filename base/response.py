from rest_framework import status
from rest_framework.response import Response
from django.core.paginator import Paginator
from typing import Any, Dict, List, Optional, Union

class APIResponse:
    """
    Standard API response format for the entire application
    """
    
    def __init__(self):
        self.status = None
        self.message = None
        self.data = None
        self.errors = None
        self.pagination = None
    
    @classmethod
    def success(
        cls, 
        message: str = "Request successful", 
        data: Any = None, 
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Success response
        """
        response_data = {
            "status": "success",
            "message": message,
            "data": data,
            "errors": None
        }
        
        if data is None:
            response_data.pop('data', None)
            
        return Response(response_data, status=status_code)
    
    @classmethod
    def _convert_errors_to_string(cls, errors: Any) -> str:
        """
        Convert errors to a single string format
        """
        if errors is None:
            return ""
            
        # If it's already a string, return as is
        if isinstance(errors, str):
            return errors
        
        # If it's a dictionary, get the first value
        if isinstance(errors, dict):
            if errors:
                first_key = next(iter(errors))
                first_value = errors[first_key]
                return cls._convert_errors_to_string(first_value)
            return "Validation error"
        
        # If it's a list, get the first item
        if isinstance(errors, list):
            if errors:
                return cls._convert_errors_to_string(errors[0])
            return "Validation error"
        
        # If it's an exception, get the message
        if isinstance(errors, Exception):
            return str(errors)
        
        # For any other type, convert to string
        return str(errors)
    
    @classmethod
    def error(
        cls, 
        message: str = "An error occurred", 
        errors: Any = None, 
        status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> Response:
        """
        Error response
        """
        response_data = {
            "status": "error",
            "message": message,
            "data": None,
        }
        
        if errors is not None:
            response_data["errors"] = cls._convert_errors_to_string(errors)
            
        return Response(response_data, status=status_code)
    
    @classmethod
    def paginated(
        cls,
        message: str = "Data retrieved successfully",
        data: Any = None,
        paginator: Paginator = None,
        page: int = 1,
        page_size: int = 20,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Paginated response
        """
        if paginator and data:
            total_items = paginator.count
            total_pages = paginator.num_pages
            total_counts = len(data)
            
            if not type(page) == int:
                page = int(page)
            if not type(page_size) == int:
                page_size = int(page_size)
            
            pagination_info = {
                "current_page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": int(page) < int(total_pages),
                "has_previous": int(page) > 1,
                "total_counts": total_counts
            }
            
            response_data = {
                "status": "success",
                "message": message,
                "data": data,
                "pagination": pagination_info,
                "errors": None
            }
        else:
            response_data = {
                "status": "success",
                "message": message,
                "data": data,
                "pagination": None,
                "errors": None
            }
        
        return Response(response_data, status=status_code)
    
    @classmethod
    def created(
        cls, 
        message: str = "Resource created successfully", 
        data: Any = None
    ) -> Response:
        """
        Resource created successfully
        """
        return cls.success(message, data, status_code=status.HTTP_201_CREATED)
    
    @classmethod
    def not_found(
        cls, 
        message: str = "Resource not found"
    ) -> Response:
        """
        Resource not found
        """
        return cls.error(message, status_code=status.HTTP_404_NOT_FOUND)
    
    @classmethod
    def unauthorized(
        cls, 
        message: str = "Authentication required"
    ) -> Response:
        """
        Unauthorized access
        """
        return cls.error(message, status_code=status.HTTP_401_UNAUTHORIZED)
    
    @classmethod
    def forbidden(
        cls, 
        message: str = "Access forbidden"
    ) -> Response:
        """
        Forbidden access
        """
        return cls.error(message, status_code=status.HTTP_403_FORBIDDEN)
    
    @classmethod
    def validation_error(
        cls, 
        message: str = "Validation error",
        errors: Any = None
    ) -> Response:
        """
        Validation error response
        """
        return cls.error(message, errors, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    @classmethod
    def server_error(
        cls, 
        message: str = "Internal server error"
    ) -> Response:
        """
        Internal server error
        """
        return cls.error(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)