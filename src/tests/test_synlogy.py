import pytest
from lib.synlogy import login, list_people
from config.config import Config

@pytest.fixture(scope="module")
def auth():
    return login(Config.SYNO_ACCOUNT, Config.SYNO_PASSWORD, Config.SYNO_FID, Config.SYNO_TIMEZONE)

def test_synology_login(auth):
    assert auth is not None
    print("✅ 成功登入 Synology")

def test_list_people(auth):
    people = list_people(auth, 5)
    assert isinstance(people, list)
    assert len(people) > 0
    print(f"✅ 成功取得 {len(people)} 筆人臉資料")
