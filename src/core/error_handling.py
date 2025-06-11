"""
Enhanced Error Handling System for Price Pilot Agents
Provides standardized error handling, validation, and user-friendly error messages
"""
import logging
import traceback
from enum import Enum
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

class ErrorCode(Enum):
    """Standardized error codes for all agents"""
    # Validation Errors (1000-1999)
    INVALID_INPUT = "1001"
    MISSING_REQUIRED_FIELD = "1002"
    INVALID_FORMAT = "1003"
    OUT_OF_RANGE = "1004"
    
    # Business Logic Errors (2000-2999)
    PRODUCT_NOT_FOUND = "2001"
    INSUFFICIENT_STOCK = "2002"
    ORDER_NOT_FOUND = "2003"
    INVALID_ORDER_STATUS = "2004"
    INVALID_SKU = "2005"
    
    # System Errors (3000-3999)
    DATABASE_ERROR = "3001"
    API_ERROR = "3002"
    TIMEOUT_ERROR = "3003"
    AUTHENTICATION_ERROR = "3004"
    RATE_LIMIT_ERROR = "3005"
    
    # Agent Errors (4000-4999)
    AGENT_TIMEOUT = "4001"
    TOOL_EXECUTION_ERROR = "4002"
    LLM_ERROR = "4003"
    DELEGATION_ERROR = "4004"
    
    # External Service Errors (5000-5999)
    SUPABASE_ERROR = "5001"
    EMBEDDING_ERROR = "5002"
    LOGISTICS_API_ERROR = "5003"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AgentError:
    """Standardized error class for all agents"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        user_message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.code = code
        self.message = message  # Technical message for logs
        self.user_message = user_message  # User-friendly message
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/API responses"""
        return {
            "code": self.code.value,
            "message": self.message,
            "user_message": self.user_message,
            "severity": self.severity.value,
            "context": self.context,
            "timestamp": self.timestamp,
            "original_error": str(self.original_error) if self.original_error else None
        }
    
    def to_user_response(self) -> str:
        """Get user-friendly response"""
        return self.user_message

class ErrorHandler:
    """Centralized error handling for all agents"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agents.{agent_name}")
        
    def handle_error(
        self,
        error: Union[Exception, AgentError],
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentError:
        """Handle and categorize errors"""
        
        if isinstance(error, AgentError):
            self._log_error(error, operation)
            return error
            
        # Categorize the exception
        agent_error = self._categorize_error(error, operation, context)
        self._log_error(agent_error, operation)
        return agent_error
    
    def _categorize_error(
        self,
        error: Exception,
        operation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentError:
        """Categorize exception into AgentError"""
        
        error_str = str(error).lower()
        
        # Database/Supabase errors
        if any(keyword in error_str for keyword in ['supabase', 'database', 'connection']):
            return AgentError(
                code=ErrorCode.DATABASE_ERROR,
                message=f"Database error in {operation}: {error}",
                user_message="I'm having trouble accessing the database. Please try again in a moment.",
                severity=ErrorSeverity.HIGH,
                context=context,
                original_error=error
            )
        
        # API/Network errors
        if any(keyword in error_str for keyword in ['api', 'network', 'timeout', 'connection']):
            return AgentError(
                code=ErrorCode.API_ERROR,
                message=f"API error in {operation}: {error}",
                user_message="I'm experiencing connectivity issues. Please try again shortly.",
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_error=error
            )
        
        # LLM/Model errors
        if any(keyword in error_str for keyword in ['model', 'llm', 'gemini', 'openai']):
            return AgentError(
                code=ErrorCode.LLM_ERROR,
                message=f"LLM error in {operation}: {error}",
                user_message="I'm having trouble processing your request. Please try rephrasing or try again.",
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_error=error
            )
        
        # Tool execution errors
        if any(keyword in error_str for keyword in ['tool', 'execution', 'parse']):
            return AgentError(
                code=ErrorCode.TOOL_EXECUTION_ERROR,
                message=f"Tool execution error in {operation}: {error}",
                user_message="I encountered an issue while processing your request. Please try again.",
                severity=ErrorSeverity.MEDIUM,
                context=context,
                original_error=error
            )
        
        # Generic error
        return AgentError(
            code=ErrorCode.AGENT_TIMEOUT,
            message=f"Unexpected error in {operation}: {error}",
            user_message="I encountered an unexpected issue. Please try again or contact support if the problem persists.",
            severity=ErrorSeverity.MEDIUM,
            context=context,
            original_error=error
        )
    
    def _log_error(self, error: AgentError, operation: str):
        """Log error with appropriate level"""
        log_data = {
            "agent": self.agent_name,
            "operation": operation,
            "error": error.to_dict()
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL ERROR in {operation}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(f"HIGH ERROR in {operation}: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"MEDIUM ERROR in {operation}: {error.message}", extra=log_data)
        else:
            self.logger.info(f"LOW ERROR in {operation}: {error.message}", extra=log_data)

class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[AgentError]:
        """Validate required fields are present and not empty"""
        missing_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return AgentError(
                code=ErrorCode.MISSING_REQUIRED_FIELD,
                message=f"Missing required fields: {missing_fields}",
                user_message=f"Please provide the following required information: {', '.join(missing_fields)}",
                severity=ErrorSeverity.LOW,
                context={"missing_fields": missing_fields}
            )
        return None
    
    @staticmethod
    def validate_email(email: str) -> Optional[AgentError]:
        """Validate email format"""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return AgentError(
                code=ErrorCode.INVALID_FORMAT,
                message=f"Invalid email format: {email}",
                user_message="Please provide a valid email address.",
                severity=ErrorSeverity.LOW,
                context={"invalid_email": email}
            )
        return None
    
    @staticmethod
    def validate_sku(sku: str) -> Optional[AgentError]:
        """Validate SKU format"""
        if not sku or len(sku.strip()) < 3:
            return AgentError(
                code=ErrorCode.INVALID_SKU,
                message=f"Invalid SKU: {sku}",
                user_message="Please provide a valid product SKU (at least 3 characters).",
                severity=ErrorSeverity.LOW,
                context={"invalid_sku": sku}
            )
        return None
    
    @staticmethod
    def validate_positive_number(value: Any, field_name: str) -> Optional[AgentError]:
        """Validate positive number"""
        try:
            num_value = float(value)
            if num_value <= 0:
                return AgentError(
                    code=ErrorCode.OUT_OF_RANGE,
                    message=f"{field_name} must be positive: {value}",
                    user_message=f"{field_name} must be a positive number.",
                    severity=ErrorSeverity.LOW,
                    context={"field": field_name, "value": value}
                )
        except (ValueError, TypeError):
            return AgentError(
                code=ErrorCode.INVALID_FORMAT,
                message=f"{field_name} must be a number: {value}",
                user_message=f"{field_name} must be a valid number.",
                severity=ErrorSeverity.LOW,
                context={"field": field_name, "value": value}
            )
        return None

def safe_agent_execution(agent_name: str, operation: str):
    """Decorator for safe agent execution with standardized error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            error_handler = ErrorHandler(agent_name)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                agent_error = error_handler.handle_error(e, operation)
                # Return error in agent response format
                return {
                    "messages": [{"type": "ai", "content": agent_error.to_user_response()}],
                    "intermediate_steps": [],
                    "error": agent_error.to_dict()
                }
        return wrapper
    return decorator
