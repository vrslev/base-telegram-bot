from json import JSONDecodeError
from typing import Any, Literal, TypeVar

import requests
from pydantic import (
    BaseModel,  # TODO: Can we just drop pydantic dependency? Or make it optional
)

__all__ = ["BaseTelegramBot", "TelegramBotError"]


class TelegramBotError(Exception):
    def __init__(self, *args: Any, response: requests.Response) -> None:
        self.response = response
        super().__init__(*args)


class BaseTelegramBotResponse(BaseModel):
    ok: Literal[True]
    result: Any


_T = TypeVar("_T", bound=BaseModel)


class BaseTelegramBot:
    def __init__(self, token: str, endpoint: str = "https://api.telegram.org"):
        self.token = token
        self.endpoint = endpoint
        self._session = requests.Session()

    def _build_url(self, method: str):
        assert method.startswith("/"), "Method name should start with slash"
        return f"{self.endpoint}/bot{self.token}{method}"

    def parse_response(
        self, *, response: requests.Response, model: type[_T] = BaseTelegramBotResponse
    ) -> _T:
        try:
            resp_json = response.json()
        except JSONDecodeError:
            raise TelegramBotError("Can't decode json response", response=response)

        if "description" in resp_json:
            response.reason = resp_json["description"]

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise TelegramBotError(*exc.args, response=response)

        return model(**resp_json)

    def make_request(
        self,
        *,
        method: str,
        model: type[_T] = BaseTelegramBotResponse,
        json: Any = None,
    ) -> _T:
        url = self._build_url(method)
        response = self._session.post(url=url, json=json)
        return self.parse_response(response=response, model=model)