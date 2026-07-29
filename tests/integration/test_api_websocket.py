from backend.api.scan_service import _event_log, _record_event
from backend.core.events import ScanEvent


def test_websocket_receives_logged_events(api_env) -> None:
    client, repo = api_env
    scan = repo.create_scan("scan-ws", "demo", "quick")
    _event_log[scan["id"]] = []
    _record_event(scan["id"], ScanEvent.create("recon", "started", 0.2))
    repo.update_scan(scan["id"], status="completed")

    with client.websocket_connect(f"/api/scans/{scan['id']}/stream") as websocket:
        first = websocket.receive_json()
        assert first["stage"] == "recon"
        second = websocket.receive_json()
        assert second["stage"] == "complete"
