
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


from app.domains.users.models import users_model  # noqa
from app.domains.auth.models import usertokens_models  # noqa
from app.domains.security import models # noqa
from app.infrastructure.outbox.models import outbox_events_model # noqa
from app.domains.master_data.models import (
    routes_model, routestations_model, 
    schedules_model, seats_model, stations_model,
    trains_model
) # noqa

