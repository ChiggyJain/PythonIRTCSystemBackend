
"""
Feature Control Decorator (Enterprise Flexible Version)
This decorator attaches feature configuration to endpoint.
Design goals:
-------------
- flexible config
- future-proof
- no strict parameters
- safe for FastAPI
- no wrapper
- only metadata storage
CustomAPIRoute will read __feature_config__.
"""


from typing import (
    Callable, Optional, Dict, Any
)


def feature_control(
    config: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Feature control decorator
    Parameters
    ----------
    config : dict | None
    Example:
    --------

    @feature_control(
        {
            "name": "v1.users.signup",
            "logging": {
                "console" : True/False,
                "file": True/False,
            },
            "rate_limit": {
                "limit": 10,
                "window": 3600
            }
        }
    )
    """

    if config is None:
        config = {}

    if not isinstance(config, dict):
        raise TypeError(
            "feature_control config must be dict or None"
        )

    def decorator(func: Callable) -> Callable:
        """
        Attach feature config to function
        """

        # store config in function
        setattr(func, "__feature_config__", config)

        return func

    return decorator