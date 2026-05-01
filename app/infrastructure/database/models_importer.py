
"""
Models Importer
This module imports all ORM models so that
SQLAlchemy Base.metadata can detect them.
Why needed?
-----------
In Domain Driven Design (DDD), models are spread across domains.
Alembic autogenerate only detects tables that are imported.
So we must import all models here.
IMPORTANT:
----------
Do NOT add logic here.
Only import models.
"""


from app.domains.users.models import users_models  # noqa
from app.domains.auth.models import usertokens_models  # noqa
from app.domains.security.models import models # noqa
from app.infrastructure.outbox.models import outbox_events_models # noqa
from app.domains.master_data.models import stations_models # noqa
from app.domains.master_data.models import trains_models # noqa
from app.domains.master_data.models import seats_models # noqa
from app.domains.master_data.models import routes_models # noqa
from app.domains.master_data.models import routestations_models # noqa
from app.domains.master_data.models import schedules_models # noqa





