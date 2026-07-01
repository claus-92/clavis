from typing import Any, Optional

import httpx


class ClavisClient:
    def __init__(self, host: Optional[str] = None, uds: str = "/tmp/clavisd.sock", transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = host or "http://clavisd"
        if transport is None and host is None:
            transport = httpx.HTTPTransport(uds=uds)
        self._client = httpx.Client(base_url=self.base_url, transport=transport)

    def request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        response = self._client.request(method, path, json=json)
        response.raise_for_status()
        return response.json()

    def status(self) -> Any:
        return self.request("GET", "/api/status")

    def list_boards(self) -> Any:
        return self.request("GET", "/api/boards")

    def list_board_types(self) -> Any:
        return self.request("GET", "/api/board-types")

    def create_board(self, config: dict[str, Any]) -> Any:
        return self.request("POST", "/api/boards", json=config)

    def discover_boards(self) -> Any:
        return self.request("POST", "/api/boards/discover")

    def get_board(self, board_id: str) -> Any:
        return self.request("GET", f"/api/boards/{board_id}")

    def get_board_config(self, board_id: str) -> Any:
        return self.request("GET", f"/api/boards/{board_id}/config")

    def get_board_status(self, board_id: str) -> Any:
        return self.request("GET", f"/api/boards/{board_id}/status")

    def get_parameters(self, board_id: str) -> Any:
        return self.request("GET", f"/api/boards/{board_id}/parameters")

    def connect_board(self, board_id: str) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/connect")

    def disconnect_board(self, board_id: str) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/disconnect")

    def power_on(self, board_id: str) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/power/on")

    def power_off(self, board_id: str) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/power/off")

    def set_global(self, board_id: str, options: dict[str, Any]) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/global", json=options)

    def set_group(self, board_id: str, group_id: str, options: dict[str, Any]) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/groups/{group_id}", json=options)

    def set_channel(self, board_id: str, channel_id: str, options: dict[str, Any]) -> Any:
        return self.request("POST", f"/api/boards/{board_id}/channels/{channel_id}", json=options)

    def close(self) -> None:
        self._client.close()
