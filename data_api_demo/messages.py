import json
import re

import msgspec

_CAMEL_TO_SNAKE_R = re.compile(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")


def camel_to_snake(value: str):
    """
    Convert CamelCase or camelCase string to snake_case.
    """
    return _CAMEL_TO_SNAKE_R.sub(r"_\1", value).lower()


INVALID_MESSAGE = json.dumps({"status": "error", "message": "Invalid message format"})


class WsAction(msgspec.Struct, tag_field="action", tag=camel_to_snake):
    pass


class PairSubscribe(WsAction):
    """
    {
      "action": "pair_subscribe",
      "pair": "4J1fbLefi5qvJ5snesqbJKasPqiGheakmfiQfqsFo3Wv_So11111111111111111111111111111111111111112"
    }
    """
    pair: str  # pair is alphabetically ordered two tokens


type WsMessage = PairSubscribe
