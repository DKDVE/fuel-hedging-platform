"""Custom exception hierarchy for the fuel hedging platform.

All exceptions inherit from HedgePlatformError and include:
- message: Human-readable error description
- error_code: Machine-readable snake_case identifier
- context: Optional additional context dict
"""

from typing import Any, Optional


class HedgePlatformError(Exception):
    """Base exception for all platform-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to API response dict."""
        return {
            "detail": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class ConstraintViolationError(HedgePlatformError):
    """Raised when hedge ratio, collateral, or coverage constraints are violated.
    
    Examples:
    - Hedge ratio exceeds HR_HARD_CAP (0.80)
    - Collateral requirement exceeds COLLATERAL_LIMIT (15% of reserves)
    - Coverage ratio exceeds MAX_COVERAGE_RATIO (1.10)
    """

    def __init__(
        self,
        message: str,
        constraint_type: str,
        current_value: float,
        limit_value: float,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = f"constraint_violation_{constraint_type}"
        full_context = {
            "constraint_type": constraint_type,
            "current_value": current_value,
            "limit_value": limit_value,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)


class DataIngestionError(HedgePlatformError):
    """Raised when external API calls fail or data quality checks fail.
    
    Examples:
    - EIA, CME, or ICE API returns non-200 status
    - Circuit breaker open due to consecutive failures
    - Data quality check fails (nulls, outliers, staleness)
    - Price tick outside 3σ bounds
    """

    def __init__(
        self,
        message: str,
        source: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = f"ingestion_error_{source}"
        full_context = {
            "source": source,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)


class ModelError(HedgePlatformError):
    """Raised when analytics models fail or degrade.
    
    Examples:
    - MAPE exceeds MAPE_ALERT threshold
    - Optimizer fails to converge
    - Insufficient historical data (n_observations < 252)
    - LSTM model file missing or corrupted
    """

    def __init__(
        self,
        message: str,
        model_name: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = f"model_error_{model_name}"
        full_context = {
            "model_name": model_name,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)


class AuthenticationError(HedgePlatformError):
    """Raised when authentication fails or token is invalid.
    
    Examples:
    - Invalid login credentials
    - JWT token expired or malformed
    - Missing authentication token
    - Token signature validation failed
    """

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, error_code, context)


class AuthorizationError(HedgePlatformError):
    """Raised when user lacks required permission or token is invalid.
    
    Examples:
    - User role lacks required permission (e.g., APPROVE_REC)
    - JWT token expired or invalid signature
    - API key authentication failed
    - Attempting to modify another user's resource
    """

    def __init__(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = "authorization_error"
        super().__init__(message, error_code, context)


class AuditError(HedgePlatformError):
    """Raised when audit log write fails.
    
    This is a critical error - audit writes must never fail silently.
    If an audit write fails, the operation should be rolled back.
    """

    def __init__(
        self,
        message: str,
        action: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = "audit_write_failed"
        full_context = {
            "action": action,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)


class BusinessRuleViolation(HedgePlatformError):
    """Raised when business rules are violated.
    
    Examples:
    - Attempting to approve an expired recommendation
    - Recommendation already in final state (APPROVED/REJECTED)
    - Duplicate recommendation for same analytics run
    - Invalid state transition
    - SLA violation (recommendation > 2 hours old)
    """

    def __init__(
        self,
        message: str,
        rule_type: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = f"business_rule_violation_{rule_type}"
        full_context = {
            "rule_type": rule_type,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)


class NotFoundError(HedgePlatformError):
    """Raised when a requested resource is not found.
    
    Examples:
    - User ID not found in database
    - Recommendation ID not found
    - Analytics run not found
    - Market data not available for date range
    """

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        error_code = f"{resource_type}_not_found"
        full_context = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            **(context or {}),
        }
        super().__init__(message, error_code, full_context)
