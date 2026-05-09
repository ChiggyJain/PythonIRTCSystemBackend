
from typing import (
    Callable, Optional, Dict, Any
)


def feature_control(
    config: Optional[Dict[str, Any]] = None,
) -> Callable:

    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise TypeError(
            "feature_control config must be dict or None"
        )
    def decorator(func: Callable) -> Callable:
        # store config in function
        setattr(func, "__feature_config__", config)
        return func
    return decorator