from sqlalchemy.orm import Session

from app.models.ticket_log import ActorType, TicketLog


def write_log(
    db: Session,
    ticket_id: int,
    actor_type: ActorType,
    action: str,
    message: str,
    actor_user_id: int | None = None,
    metadata_json: str | None = None,
) -> TicketLog:
    log = TicketLog(
        ticket_id=ticket_id,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        message=message,
        metadata_json=metadata_json,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_logs_by_ticket(db: Session, ticket_id: int) -> list[TicketLog]:
    return (
        db.query(TicketLog)
        .filter(TicketLog.ticket_id == ticket_id)
        .order_by(TicketLog.created_at.asc())
        .all()
    )