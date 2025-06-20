import pytest
from unittest.mock import patch, MagicMock
from service.google_service import get_photos_upload_to_album
import unittest

@pytest.fixture(scope="module")
def auth():
    return {"data": {"synotoken": "fake_token"}}


@patch("utils.sync_utils.background_sync_and_upload")
@patch("models.database.SessionLocal")
@patch("lib.synlogy.list_photos_by_person")
@patch("utils.sync_utils.needs_sync_warning")
@patch("service.synology_service.random_pick_from_person_database")
@patch("service.synology_service.save_photos_to_db_with_person")
def test_get_photos_upload_to_album_success(
    mock_save_photos,
    mock_random_pick,
    mock_needs_sync_warning,
    mock_list_photos,
    mock_session_local,
    mock_background_sync,
):
    # 1. mock DB 回傳有照片，避免走同步流程
    mock_photo = MagicMock()
    mock_photo.item_id = "123"
    mock_query = MagicMock()
    mock_query.join.return_value.filter.return_value.all.return_value = [mock_photo]
    mock_session = MagicMock()
    mock_session.query.return_value = mock_query
    mock_session_local.return_value = mock_session

    # 2. 不需要同步，回傳 False 和訊息
    mock_needs_sync_warning.return_value = (False, ["✔️ 同步狀態良好"])

    # 3. 回傳真實照片與隨機照片
    mock_list_photos.return_value = [{"id": "photoA"}]
    mock_random_pick.return_value = [{"id": "photoB"}]

    # 4. 呼叫被測試函式
    auth = {"data": {"synotoken": "fake_token"}}
    result = get_photos_upload_to_album(auth, "123", 5, "tokenXYZ")

    # 5. 驗證結果
    assert result["messages"] == ["✔️ 同步狀態良好"]
    assert result["photos"] == [{"id": "photoB"}]

class TestGetPhotosUploadToAlbum(unittest.TestCase):
    @patch("utils.sync_utils.background_sync_and_upload")
    @patch("utils.sync_utils.needs_sync_warning")
    @patch("models.database.SessionLocal")
    @patch("lib.synlogy.list_photos_by_person")
    @patch("threading.Timer")
    def test_get_photos_upload_to_album_needs_sync(
        self,
        mock_timer,
        mock_list_photos,
        mock_session_local,
        mock_needs_sync_warning,
        mock_background_sync
    ):

        mock_db = MagicMock()
        mock_photo = MagicMock()
        mock_photo.item_id = "123"
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_photo]
        mock_session_local.return_value = mock_db


        mock_needs_sync_warning.return_value = (
            True,
            ["✅ 任務已提交，由於您是第一次上傳，系統將在背景同步資料與上傳照片，需等候數十分鐘，請稍後再試"],
        )
        mock_list_photos.return_value = []

        mock_timer_instance = MagicMock()
        mock_timer.return_value = mock_timer_instance

        auth = {"data": {"synotoken": "fake_token"}}
        result = get_photos_upload_to_album(auth, "123", 5, "tokenXYZ")

        self.assertIn("背景同步", result["messages"][0])
        mock_timer.assert_called_once()
        mock_timer_instance.start.assert_called_once()


def test_get_photos_upload_to_album_no_person_id(auth):
    result = get_photos_upload_to_album(auth, None, 5, "tokenXYZ")
    assert "person_id 為空" in result["messages"][0]
