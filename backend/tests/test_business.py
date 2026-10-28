import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import order_service, ticket_service
from app.db.session import SessionLocal
from app.models.ticket import TicketStatus, RiskLevel, AfterSalesType
from app.models.user import User as UserModel
from app.models.order import Order as OrderModel


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["data"]["token"]["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _get_user_id(db: SessionLocal, username: str) -> int:
    return db.query(UserModel).filter(UserModel.username == username).first().id


def _bob_order_id(db: SessionLocal) -> int:
    bob_id = _get_user_id(db, "bob")
    order = db.query(OrderModel).filter(OrderModel.user_id == bob_id).first()
    assert order, "bob should have orders"
    return order.id


class TestOrderQueries:
    def test_alice_can_list_own_orders(self, client):
        token = _login(client, "alice", "seed123456")
        resp = client.get("/api/orders", headers=_headers(token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2

    def test_alice_can_get_own_order_detail(self, client):
        token = _login(client, "alice", "seed123456")
        resp = client.get("/api/orders", headers=_headers(token))
        first_id = resp.json()["data"][0]["id"]
        resp2 = client.get(f"/api/orders/{first_id}", headers=_headers(token))
        assert resp2.status_code == 200
        assert resp2.json()["data"]["id"] == first_id

    def test_alice_cannot_get_bobs_order(self, client):
        db = SessionLocal()
        bid = _bob_order_id(db)
        db.close()

        token = _login(client, "alice", "seed123456")
        resp = client.get(f"/api/orders/{bid}", headers=_headers(token))
        assert resp.status_code == 404

    def test_unauth_order_list_401(self, client):
        resp = client.get("/api/orders")
        assert resp.status_code == 401


class TestTicketFlow:
    def test_create_ticket_success(self, client):
        alice_token = _login(client, "alice", "seed123456")
        db = SessionLocal()
        alice_id = _get_user_id(db, "alice")
        db.close()

        resp = client.get("/api/orders", headers=_headers(alice_token))
        order_id = resp.json()["data"][0]["id"]

        resp2 = client.post(
            "/api/tickets",
            json={
                "order_id": order_id,
                "after_sales_type": "refund_only",
                "reason": "测试退款，商品有质量问题",
                "risk_level": "low",
            },
            headers=_headers(alice_token),
        )
        assert resp2.status_code == 200
        data = resp2.json()["data"]
        assert data["ticket_no"].startswith("TK-")
        assert data["status"] == "completed"
        assert data["user_id"] == alice_id

    def test_alice_can_list_own_tickets(self, client):
        token = _login(client, "alice", "seed123456")
        resp = client.get("/api/tickets", headers=_headers(token))
        assert resp.status_code == 200

    def test_alice_cannot_view_bob_ticket(self, client):
        db = SessionLocal()
        bob_id = _get_user_id(db, "bob")
        from app.models.ticket import Ticket
        bob_ticket = db.query(Ticket).filter_by(user_id=bob_id).first()
        if not bob_ticket:
            bob_order = db.query(OrderModel).filter(OrderModel.user_id == bob_id).first()
            from app.models.chat_session import ChatSession
            session = db.query(ChatSession).filter_by(user_id=bob_id).first()
            if not session:
                session = ChatSession(user_id=bob_id, thread_id=f"thread-{bob_id}")
                db.add(session)
                db.commit()
                db.refresh(session)
            bob_ticket = ticket_service.create_ticket(
                db, user_id=bob_id, order_id=bob_order.id, session_id=session.id,
                after_sales_type=AfterSalesType.return_refund, reason="bob 测试工单",
                risk_level=RiskLevel.low,
            )
        bid = bob_ticket.id
        db.close()

        token = _login(client, "alice", "seed123456")
        resp = client.get(f"/api/tickets/{bid}", headers=_headers(token))
        assert resp.status_code == 404

    def test_admin_can_view_any_ticket(self, client):
        token = _login(client, "admin", "admin123456")
        db = SessionLocal()
        from app.models.ticket import Ticket
        any_ticket = db.query(Ticket).first()
        any_id = any_ticket.id if any_ticket else None
        db.close()
        if any_id:
            resp = client.get(f"/api/tickets/{any_id}", headers=_headers(token))
            assert resp.status_code == 200


class TestTicketLogs:
    def test_ticket_has_creation_log(self, client):
        db = SessionLocal()
        from app.models.ticket import Ticket as TicketModel
        before = db.query(TicketModel).count()
        db.close()

        token = _login(client, "alice", "seed123456")
        resp = client.get("/api/orders", headers=_headers(token))
        if not resp.json()["data"]:
            pytest.skip("no orders")
        order_id = resp.json()["data"][0]["id"]
        resp2 = client.post(
            "/api/tickets",
            json={
                "order_id": order_id,
                "after_sales_type": "refund_only",
                "reason": "for log test",
                "risk_level": "low",
            },
            headers=_headers(token),
        )
        assert resp2.status_code == 200
        tid = resp2.json()["data"]["id"]
        resp3 = client.get(f"/api/tickets/{tid}/logs", headers=_headers(token))
        assert resp3.status_code == 200
        logs = resp3.json()["data"]
        assert any(l["action"] == "TICKET_CREATED" for l in logs)


class TestStatusGuard:
    def test_cannot_transition_completed(self):
        from app.services.ticket_service import ensure_valid_transition
        with pytest.raises(Exception) as exc:
            ensure_valid_transition(TicketStatus.completed, TicketStatus.pending)
        assert "INVALID_STATUS_TRANSITION" in str(exc.value.error_code)


class TestSimulateAfterSales:
    def test_cannot_execute_twice(self, client):
        import datetime as dt
        db = SessionLocal()
        from app.models.ticket import Ticket as TicketModel
        from app.models.chat_session import ChatSession
        from app.services import ticket_service as ts
        alice_id = _get_user_id(db, "alice")
        order = db.query(OrderModel).filter(OrderModel.user_id == alice_id).first()
        if not order:
            db.close()
            pytest.skip("no order")
        session = db.query(ChatSession).filter_by(user_id=alice_id).first()
        if not session:
            session = ChatSession(user_id=alice_id, thread_id=f"thread-{alice_id}")
            db.add(session)
            db.commit()
            db.refresh(session)
        ticket = ts.create_ticket(
            db, user_id=alice_id, order_id=order.id, session_id=session.id,
            after_sales_type=AfterSalesType.return_refund, reason="dup exec test",
            risk_level=RiskLevel.low,
        )
        ticket.operation_completed_at = dt.datetime.utcnow()
        db.commit()
        tid = ticket.id
        db.close()

        db2 = SessionLocal()
        with pytest.raises(Exception) as exc:
            ts.simulate_after_sales_execution(db2, ticket_id=tid)
        db2.close()
        assert "ALREADY_EXECUTED" in str(exc.value.error_code)