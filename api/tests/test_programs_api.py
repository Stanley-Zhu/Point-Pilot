"""The /programs routes, called over HTTP through TestClient."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Account, Program

HYATT = {"name": "World of Hyatt", "kind": "hotel", "currency_name": "points"}


def create(client: TestClient, **overrides: object) -> dict[str, Any]:
    """POST a valid program; tests override only the fields they are checking."""
    response = client.post("/programs", json={**HYATT, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_returns_the_program_with_its_id(client: TestClient) -> None:
    program = create(client)

    assert program == {**HYATT, "id": program["id"], "expiry_rule": None}


def test_list_returns_programs_by_name(client: TestClient) -> None:
    create(client, name="World of Hyatt")
    create(client, name="Chase Ultimate Rewards", kind="bank")

    response = client.get("/programs")

    assert response.status_code == 200
    assert [p["name"] for p in response.json()] == ["Chase Ultimate Rewards", "World of Hyatt"]


def test_duplicate_name_is_a_conflict(client: TestClient) -> None:
    create(client)

    response = client.post("/programs", json=HYATT)

    assert response.status_code == 409


def test_unknown_kind_is_rejected_before_the_database(client: TestClient) -> None:
    response = client.post("/programs", json={**HYATT, "kind": "cruise"})

    assert response.status_code == 422


def test_empty_name_is_rejected(client: TestClient) -> None:
    response = client.post("/programs", json={**HYATT, "name": ""})

    assert response.status_code == 422


def test_delete_removes_an_unused_program(client: TestClient) -> None:
    program = create(client)

    response = client.delete(f"/programs/{program['id']}")

    assert response.status_code == 204
    assert client.get("/programs").json() == []


def test_delete_unknown_program_is_not_found(client: TestClient) -> None:
    response = client.delete("/programs/999999")

    assert response.status_code == 404


def test_program_with_accounts_cannot_be_deleted(client: TestClient, db: Session) -> None:
    program = create(client)
    # No POST /accounts yet, so add the account straight through the session.
    # commit() only releases a savepoint here; the test's outer transaction still rolls back.
    db.add(Account(program_id=program["id"], member_ref="1234"))
    db.commit()

    response = client.delete(f"/programs/{program['id']}")

    assert response.status_code == 409
    # The failed delete rolled back, so the program is still there.
    assert db.get(Program, program["id"]) is not None
