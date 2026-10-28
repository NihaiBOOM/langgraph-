import pytest
from app.db.session import SessionLocal
from app.models.order import Order, AfterSalesStatus
from app.models.ticket import Ticket
from app.models.ticket_log import TicketLog
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession


def _reset_db():
    db = SessionLocal()
    try:
        for o in db.query(Order).all():
            o.after_sales_status = AfterSalesStatus.none
        for t in db.query(Ticket).all():
            db.delete(t)
        for l in db.query(TicketLog).all():
            db.delete(l)
        for m in db.query(ChatMessage).all():
            db.delete(m)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_state_between_tests():
    _reset_db()
    yield