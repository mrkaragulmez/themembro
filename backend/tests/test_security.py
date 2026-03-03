# backend/tests/test_security.py
# Faz 5 - JWT guvenlik birim testleri
# Yalnizca python-jose + pydantic gerektirir, her ortamda calisir.
# HTTP/RLS entegrasyon testleri: tests/test_api_security.py

from __future__ import annotations
import pytest
from app.core.security import decode_token, decode_refresh_token
from jose import JWTError
from tests.conftest import TENANT_A_ID, TENANT_B_ID, USER_A_ID


class TestTokenTypeValidation:

    def test_access_token_decoded_correctly(self, tenant_a_token):
        payload = decode_token(tenant_a_token, expected_type="access")
        assert payload.sub == USER_A_ID
        assert payload.tenant_id == TENANT_A_ID

    def test_refresh_token_rejected_as_access(self, refresh_token_a):
        with pytest.raises(JWTError):
            decode_token(refresh_token_a, expected_type="access")

    def test_access_token_rejected_as_refresh(self, tenant_a_token):
        with pytest.raises(JWTError):
            decode_refresh_token(tenant_a_token)

    def test_refresh_token_decoded_correctly(self, refresh_token_a):
        payload = decode_refresh_token(refresh_token_a)
        assert payload.sub == USER_A_ID

    def test_tenant_id_preserved_in_token(self, tenant_a_token):
        payload = decode_token(tenant_a_token)
        assert payload.tenant_id == TENANT_A_ID

    def test_tenant_b_has_different_tenant(self, tenant_a_token, tenant_b_token):
        pa = decode_token(tenant_a_token)
        pb = decode_token(tenant_b_token)
        assert pa.tenant_id != pb.tenant_id
        assert pa.tenant_id == TENANT_A_ID
        assert pb.tenant_id == TENANT_B_ID

    def test_tampered_token_rejected(self):
        with pytest.raises(JWTError):
            decode_token("not.a.valid.jwt.token")

    def test_empty_token_rejected(self):
        with pytest.raises(JWTError):
            decode_token("")
