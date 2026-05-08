
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.common.utils.datetime import now_ist
from app.core.exceptions import BaseAppException
from app.domains.master_data.repository.sqlalchemy_repo import MasterDataSQLAlchemyRepository
from app.infrastructure.outbox.repository.sqlalchemy_repo import OutboxEventsSQLAlchemyRepository


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
        train_number: str,
        train_name: str,
        coach_name: str,
        total_seats: int,
        seat_details: list[dict],
        admin_user_id: int,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict:
        
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

        try:

            # 1) create train
            train = await self.masterdata_repo.create_train(
                train_number=normalized_train_number,
                train_name=train_name,
                coach_name=normalized_coach_name,
                total_seats=total_seats,
                status="A",
            )

            # 2) create seats under same train_id
            seats = await self.masterdata_repo.create_seats(
                train_id=train.id,
                seat_details=normalized_seat_details,
                status="A",
            )

            # 3) create outbox event snapshot
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
                            # Decimal -> JSON-safe primitive
                            "price": float(seat.price) if isinstance(seat.price, Decimal) else seat.price,
                            "status": seat.status,
                        }
                        for seat in seats
                    ],
                    "event_type": self.OUTBOX_EVENT_TRAIN_CREATED,
                    "event_version": 1,
                    "created_by_admin_user_id": admin_user_id,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "event_created_at": str(now_ist()),
                },
                status=self.OUTBOX_STATUS_PENDING,
            )

            # 4) single commit for train + seats + outbox
            await self._db_session.commit()

        # handling rollback cases if any exception is occured
        except IntegrityError as ex:
            await self._db_session.rollback()
            msg = str(getattr(ex, "orig", ex)).lower()
            if "uq_train_number" in msg or "train_number" in msg:
                raise BaseAppException(
                    status_code=400,
                    messages=["Train number already exists"],
                )
            if "uq_trainid_seatnumber" in msg or "train_id" in msg or "seat_number" in msg:
                raise BaseAppException(
                    status_code=400,
                    messages=["Seat number conflict for this train"],
                )
            raise BaseAppException(
                status_code=400,
                messages=["Unable to create train due to data constraint violation"],
            )
        except Exception:
            await self._db_session.rollback()
            raise

        return {
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
