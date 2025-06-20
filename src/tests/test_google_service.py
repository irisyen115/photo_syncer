import unittest
from unittest.mock import MagicMock
from lib.google import get_or_create_album

class TestGooglePhotosAPI(unittest.TestCase):
    def test_get_or_create_album_album_exists(self):
        # 模擬 service.albums().list() 回傳一個已有的相簿
        service = MagicMock()
        service.albums().list().execute.return_value = {
            "albums": [
                {"id": "album123", "title": "My New Album"},
                {"id": "album456", "title": "Other Album"}
            ]
        }
        album_id = get_or_create_album(service, "My New Album")
        self.assertEqual(album_id, "album123")
        # 確定沒有呼叫 create，因為相簿已存在
        service.albums().create.assert_not_called()

    def test_get_or_create_album_album_not_exists(self):
        # 模擬 service.albums().list() 回傳沒有相簿
        service = MagicMock()
        service.albums().list().execute.return_value = {
            "albums": [
                {"id": "xyz789", "title": "Other Album"}
            ]
        }

        # 模擬 create 回傳的 album id
        mock_create = service.albums().create
        mock_create.return_value.execute.return_value = {"id": "new_album_789"}

        album_id = get_or_create_album(service, "My New Album")
        self.assertEqual(album_id, "new_album_789")

        # ✅ 改成這樣，檢查是否呼叫正確的 body 參數
        mock_create.assert_called_once_with(body={"album": {"title": "My New Album"}})

if __name__ == "__main__":
    unittest.main()
