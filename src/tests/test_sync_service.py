# tests/test_sync_service.py
import pytest
import threading
import time

from unittest.mock import patch, MagicMock

@patch("service.sync_service.get_service")
@patch("service.sync_service.get_or_create_album")
@patch("service.sync_service.update_people_list")
@patch("service.sync_service.delete_all_photos_from_album")
@patch("service.sync_service.run_sync")
@patch("service.sync_service.requests.post")
def test_background_sync_success(
    mock_requests_post,
    mock_run_sync,
    mock_delete_photos,
    mock_update_people,
    mock_create_album,
    mock_get_service
):
    from service.sync_service import background_sync

    # 模擬傳回值
    mock_get_service.return_value = "mock_service"
    mock_create_album.return_value = "mock_google_album_id"
    mock_run_sync.return_value = {
        "uploaded": 5,
        "messages": ["mock success"]
    }

    # 建立假資料
    global creds, auth, token, album_name, person_id, album_id, num_photos, start_time
    creds = "mock_creds"
    auth = "mock_auth"
    token = "mock_token"
    album_name = "test_album"
    person_id = "123"
    album_id = None
    num_photos = 5
    start_time = time.time()

    # 執行測試（背景執行，這裡為同步測試直接調用）
    background_sync(creds, auth, token, album_name, person_id, album_id, num_photos, start_time)


    mock_get_service.assert_called_once()
    mock_create_album.assert_called_once()
    mock_update_people.assert_called_once()
    mock_delete_photos.assert_called_once()
    mock_run_sync.assert_called_once()
    mock_requests_post.assert_called_with(
        "https://irisyen115.synology.me/api/line/notify",
        json={"message": "✅ 上傳完成，共上傳 5 張照片", "token": "mock_token"}
    )
