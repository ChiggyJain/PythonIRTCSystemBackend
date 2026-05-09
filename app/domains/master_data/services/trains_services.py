
from decimal import Decimal
from aiohttp import payload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.core.response import (
    success_response, 
    error_response,
    exception_response
)
from app.core.settings import get_settings
from app.common.utils.ratelimiter import rate_limiter
from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


settings = get_settings()


class TrainsService:

    OUTBOX_STATUS_PENDING = "PENDING"
    OUTBOX_EVENT_TRAIN_CREATED = "MASTERDATA_TRAIN_CREATED"

    def __init__(self, db_session: AsyncSession):
        self._db_session = db_session
        self.masterdata_repo = MasterDataSQLAlchemyRepository(db_session)
        self.outbox_repo = OutboxEventsSQLAlchemyRepository(db_session)


    async def create_train(
        self,
        *,
        payload: dict
    ) -> dict:
        
        try:

            # extracted parameters
            train_number = payload.get("train_number", "")
            train_name = payload.get("train_name", "")
            coach_name = payload.get("coach_name", "AC")
            total_seats = int(payload.get("total_seats", 0))
            seat_details = payload.get("seat_details", [])
            user_id = payload.get("user_id", 0)
            correlation_id = payload.get("correlation_id", "")
            request_id = payload.get("request_id", "")
            
            # Locked normalization rule
            normalized_train_number = (train_number or "").strip().upper()
            normalized_coach_name = (coach_name or "").strip().upper()

            # Normalize seat_type to uppercase (defensive layer)
            normalized_seat_details = []
            for seat in seat_details:
                normalized_seat_details.append(
                    {
                        "seat_number": seat["seat_number"],
                        "seat_type": (seat["seat_type"] or "").strip().upper(),
                        "price": seat["price"],
                    }
                )

            # User-level limiter for train creation
            user_rate_key = f"user:trains:create:{user_id}"
            user_allowed_request = await rate_limiter.check_window_limit(
                key=user_rate_key,
                limit=settings.MASTERDATA_TRAIN_CREATE_USER_RATE_LIMIT,
                window=settings.MASTERDATA_TRAIN_CREATE_USER_RATE_WINDOW_SECONDS,
            )
            if not user_allowed_request:
                return error_response(
                    status_code=429,
                    messages=["Too many train create requests. Please try again later."],
                )

            # create train
            train = await self.masterdata_repo.create_train(
                train_number=normalized_train_number,
                train_name=train_name,
                coach_name=normalized_coach_name,
                total_seats=total_seats,
                status="A",
            )

            # create seats under same train_id
            seats = await self.masterdata_repo.create_seats(
                train_id=train.id,
                seat_details=normalized_seat_details,
                status="A",
            )

            # create outbox event snapshot
            await self.outbox_repo.add_outbox_event(
                aggregate_type="TRAIN",
                aggregate_id=str(train.id),
                event_type=self.OUTBOX_EVENT_TRAIN_CREATED,
                payload_json={
                    "train_id": train.id,
                    "train_number": train.train_number,
                    "train_name": train.train_name,
                    "coach_name": train.coach_name,
                    "total_seats": train.total_seats,
                    "status": train.status,
                    "seat_details": [
                        {
                            "id": seat.id,
                            "seat_number": seat.seat_number,
                            "seat_type": seat.seat_type,
                            "price": float(seat.price) if isinstance(seat.price, Decimal) else seat.price,
                            "status": seat.status,
                        }
                        for seat in seats
                    ],
                    "event_type": self.OUTBOX_EVENT_TRAIN_CREATED,
                    "event_version": 1,
                    "created_by_user_id": user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            await self._db_session.commit()

            return success_response(
                status_code=201,
                messages=[f""],
                data={
                    "id": train.id,
                    "train_number": train.train_number,
                    "train_name": train.train_name,
                    "coach_name": train.coach_name,
                    "total_seats": train.total_seats,
                    "status": train.status,
                    "seat_details": [
                        {
                            "id": seat.id,
                            "seat_number": seat.seat_number,
                            "seat_type": seat.seat_type,
                            "price": float(seat.price) if isinstance(seat.price, Decimal) else seat.price,
                            "status": seat.status,
                        }
                        for seat in seats
                    ],
                    "dispatch_status": "accepted",
                }
            )
        
        except IntegrityError as ex:
            await self._db_session.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            return error_response(
                status_code=400,
                messages=[f"Unable to create train due to data constraint violation. {msg}"],
            )
        
        except BaseAppException as e:
            await self._db_session.rollback()
            raise e
        
        except Exception as e:
            await self._db_session.rollback()
            return exception_response(
                status_code=500,
                messages=[f"{str(e)}"]
            )

        
