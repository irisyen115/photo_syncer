from unittest.mock import MagicMock, patch

import lib.google as g


def _service(statuses):
    service = MagicMock()
    responses = [(MagicMock(status=s), b"{}") for s in statuses]
    service._http.request.side_effect = responses
    return service


@patch("lib.google.get_or_create_album", return_value="trash_id")
@patch("lib.google.get_media_items_in_album")
def test_adds_in_batches_below_50(mock_items, _mock_album):
    mock_items.return_value = [f"id{i}" for i in range(200)]
    service = _service([200] * 5)

    assert g.move_items_to_trash_album(service, "album") is True

    sizes = [len(__import__("json").loads(c.kwargs["body"])["mediaItemIds"])
             for c in service._http.request.call_args_list]
    assert sizes == [49, 49, 49, 49, 4]
    assert all(s < 50 for s in sizes)


@patch("lib.google.get_or_create_album", return_value="trash_id")
@patch("lib.google.get_media_items_in_album")
def test_returns_false_and_stops_on_failure(mock_items, _mock_album):
    mock_items.return_value = [f"id{i}" for i in range(120)]
    service = _service([200, 400, 200])

    assert g.move_items_to_trash_album(service, "album") is False
    assert service._http.request.call_count == 2


@patch("lib.google.get_or_create_album")
@patch("lib.google.get_media_items_in_album", return_value=[])
def test_empty_album_is_success_without_requests(_mock_items, mock_album):
    service = _service([])

    assert g.move_items_to_trash_album(service, "album") is True
    service._http.request.assert_not_called()
    mock_album.assert_not_called()
