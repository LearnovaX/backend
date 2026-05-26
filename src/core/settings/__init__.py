"""
Settings package resolver.

Reads DJANGO_ENV from environment and imports the corresponding settings module.
Every other module in the project can use ``src.core.settings`` as the settings path.

When DJANGO_SETTINGS_MODULE points directly at a sub-module (e.g., ``src.core.settings.test``),
this file is still executed as the package __init__, but we skip the dynamic import so the
sub-module's own ``from .base import *`` is the only thing that configures Django.
"""

import os

_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")

# Only resolve dynamically when the settings module is this package itself
if _settings_module == "src.core.settings" or not _settings_module:
    # Import env from base first so it's available to all settings modules
    from .base import env  # noqa: F401

    DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev")

    if DJANGO_ENV == "prod":
        from .prod import *  # noqa: F401, F403
    elif DJANGO_ENV == "test":
        from .test import *  # noqa: F401, F403
    else:  # dev is default
        from .dev import *  # noqa: F401, F403
