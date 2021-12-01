from __future__ import annotations

from copy import copy
from json import JSONDecodeError
from typing import Any

import pytest
import requests
import responses
from pydantic import BaseModel

from base_telegram_bot import BaseTelegramBot, BaseTelegramBotResponse, TelegramBotError


@pytest.fixture
def token():
    return "some token value"


@pytest.fixture
def bot(token: str):
    return BaseTelegramBot(token)


def test_build_url_not_slash(bot: BaseTelegramBot):
    with pytest.raises(AssertionError, match="Method name should start with slash"):
        bot._build_url("getUpdates")


def test_build_url_default_endpoint(bot: BaseTelegramBot):
    default_endpoint = copy(bot.endpoint)
    assert bot._build_url("/getUpdates").startswith(default_endpoint)


def test_build_url_custom_endpoint(bot: BaseTelegramBot):
    custom_endpoint = "https://example.com"
    bot.endpoint = copy(custom_endpoint)
    assert bot._build_url("/getUpdates").startswith(custom_endpoint)


def test_build_url_main(bot: BaseTelegramBot, token: str):
    method = "/getUpdates"
    assert bot._build_url(copy(method)) == f"{bot.endpoint}/bot{token}{method}"


def test_parse_response_not_json(bot: BaseTelegramBot):
    class MyResponse:
        def json(self):
            raise JSONDecodeError("", "", 0)

    response = MyResponse()
    with pytest.raises(TelegramBotError, match="Can't decode json response") as exc:
        bot.parse_response(response=response)  # type: ignore
    assert exc.value.response == response


def test_parse_response_no_description(bot: BaseTelegramBot):
    class MyResponse:
        reason: str | None = None

        def json(self) -> dict[Any, Any]:
            return {}

        def raise_for_status(self):
            raise requests.HTTPError

    response = MyResponse()
    with pytest.raises(TelegramBotError):
        bot.parse_response(response=response)  # type: ignore
    assert response.reason is None


def test_parse_response_with_description(bot: BaseTelegramBot):
    class MyResponse:
        reason: str | None = None

        def json(self) -> dict[Any, Any]:
            return {"description": "Not Found"}

        def raise_for_status(self):
            raise requests.HTTPError

    response = MyResponse()
    with pytest.raises(TelegramBotError):
        bot.parse_response(response=response)  # type: ignore
    assert response.reason == "Not Found"


def test_parse_response_http_error(bot: BaseTelegramBot):
    args = ("one", "two")

    class MyResponse:
        def json(self) -> dict[Any, Any]:
            return {}

        def raise_for_status(self):
            raise requests.HTTPError(*copy(args))

    response = MyResponse()
    with pytest.raises(TelegramBotError) as exc:
        bot.parse_response(response=response)  # type: ignore
    assert exc.value.args == args
    assert exc.value.response == response


def test_parse_response_returns_default_model(bot: BaseTelegramBot):
    exp_result = "my result"

    class MyResponse:
        def json(self) -> dict[Any, Any]:
            return {"ok": True, "result": exp_result}

        def raise_for_status(self):
            pass

    assert bot.parse_response(
        response=MyResponse()  # type: ignore
    ) == BaseTelegramBotResponse(ok=True, result=exp_result)


def test_parse_response_returns_custom_model(bot: BaseTelegramBot):
    exp_result = {"foo": "foo", "bar": 1}

    class CustomResponseResult(BaseModel):
        foo: str
        bar: int

    class CustomResponse(BaseTelegramBotResponse):
        result: CustomResponseResult

    class MyResponse:
        def json(self) -> dict[Any, Any]:
            return {"ok": True, "result": exp_result}

        def raise_for_status(self):
            pass

    assert bot.parse_response(
        response=MyResponse(), model=CustomResponse  # type: ignore
    ) == CustomResponse(ok=True, result=exp_result)


@pytest.mark.parametrize("endpoint", ("https://example.com", None))
@responses.activate
def test_make_request(bot: BaseTelegramBot, token: str, endpoint: str | None):
    if endpoint is not None:
        bot.endpoint = copy(endpoint)
    else:
        endpoint = copy(bot.endpoint)
    responses.add(
        method=responses.POST,
        url=f"{endpoint}/bot{token}/getUpdates",
        json={"ok": True, "result": {"foo": "bar"}},
        match=[responses.matchers.json_params_matcher({"id": 101})],  # type: ignore
    )

    class GetUpdatesResult(BaseModel):
        foo: str

    class GetUpdatesResponse(BaseTelegramBotResponse):
        result: GetUpdatesResult

    bot.make_request(method="/getUpdates", model=GetUpdatesResponse, json={"id": 101})
