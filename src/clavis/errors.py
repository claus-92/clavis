import httpx


class ClavisAPIError(httpx.HTTPStatusError):
    """HTTP error returned by the Clavis daemon.

    This exception is raised by ClavisClient for non-2xx responses.
    It carries the server-provided "detail" string when present in the JSON body,
    and remains a subclass of httpx.HTTPStatusError so existing error handlers continue to work.
    """

    def __init__(self, message: str, *, request: httpx.Request, response: httpx.Response) -> None:
        super().__init__(message, request=request, response=response)
        self.detail: str | None = self._extract_detail(response)

    @staticmethod
    def _extract_detail(response: httpx.Response) -> str | None:
        try:
            data = response.json()
            if isinstance(data, dict):
                d = data.get("detail")
                if isinstance(d, str):
                    return d
        except Exception:
            pass
        return None
