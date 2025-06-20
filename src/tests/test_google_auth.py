import os
import pytest
from lib.google import authenticate, get_service

def test_authenticate():
    creds = authenticate()
    assert creds is not None, "❌ 無法取得 Google OAuth 憑證"
    assert creds.valid, "❌ 憑證無效"
    print("✅ 成功取得並驗證憑證")

def test_get_service():
    creds = authenticate()
    service = get_service(creds)
    assert service is not None, "❌ 無法建立 Google Photos 服務"
    print("✅ 成功建立 Google Photos 服務")
