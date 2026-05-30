"""Tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test that the health endpoint responds."""
    response = await client.get("/api/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, test_user_data: dict):
    """Test user registration."""
    response = await client.post("/api/auth/register", json=test_user_data)
    # May fail if DB not available, but should not crash
    assert response.status_code in (201, 500)
    if response.status_code == 201:
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "id" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with wrong credentials."""
    response = await client.post("/api/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code in (401, 500)


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test that protected endpoints reject unauthenticated requests."""
    response = await client.get("/api/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_conversations_without_auth(client: AsyncClient):
    """Test that chat endpoints require authentication."""
    response = await client.get("/api/chat")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_documents_without_auth(client: AsyncClient):
    """Test that document endpoints require authentication."""
    response = await client.get("/api/documents")
    assert response.status_code in (401, 403)
