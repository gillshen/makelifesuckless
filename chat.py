import dataclasses
import json
import re
import typing
import argparse

import openai
import tiktoken

MAX_TOKENS = 4097

try:
    with open("chat_settings.json", encoding="utf-8") as f:
        chat_settings = json.load(f)
    openai.api_key = chat_settings["key"]
    if "base" in chat_settings:
        openai.api_base = chat_settings["base"]
    if "max_tokens" in chat_settings:
        MAX_TOKENS = chat_settings["max_tokens"]
    del chat_settings
except (FileNotFoundError, json.JSONDecodeError):
    openai.api_key = ""

try:
    tiktoken.get_encoding("cl100k_base")
    tiktoken.get_encoding("p50k_base")
    _TIKTOKEN_READY = True
except Exception:
    _TIKTOKEN_READY = False


@dataclasses.dataclass
class Params:
    """A selection of parameters of openai.ChatCompletion.create()"""

    # Recommended models:
    # - gpt-4
    # - gpt-3.5-turbo (default)
    # - text-davinci-003
    model: str = "gpt-3.5-turbo"

    # OpenAI doc:
    # What sampling temperature to use, between 0 and 2. Higher values
    # like 0.8 will make the output more random, while lower values
    # like 0.2 will make it more focused and deterministic.
    # We generally recommend altering this or `top_p` but not both.
    temperature: float = None

    # OpenAI doc:
    # An alternative to sampling with temperature, called nucleus sampling,
    # where the model considers the results of the tokens with `top_p`
    # probability mass. So 0.1 means only the tokens comprising the top
    # 10% probability mass are considered.
    # We generally recommend altering this or `temperature` but not both.
    top_p: float = None

    # OpenAI doc:
    # Number between -2.0 and 2.0. Positive values penalize new tokens
    # based on whether they appear in the text so far, increasing the
    # model's likelihood to talk about new topics.
    presence_penalty: float = None

    # OpenAI doc:
    # Number between -2.0 and 2.0. Positive values penalize new tokens
    # based on their existing frequency in the text so far, decreasing
    # the model's likelihood to repeat the same line verbatim.
    frequency_penalty: float = None

    @classmethod
    def from_json(cls, filepath: str) -> "Params":
        with open(filepath, encoding="utf-8") as f:
            return cls(**json.load(f))


class Chat:
    def __init__(self, system_message="You are a helpful assistant."):
        self.system_message = system_message
        self.messages = []
        self.reserve_level = 75
        self.reset_messages()

    def reset_messages(self):
        self.messages = [{"role": "system", "content": self.system_message}]

    def send(self, prompt: str, *, keep_context: bool = False, **kwargs):
        # `keep_context`:
        # if true, GPT responses are kept as assistant messages and
        # sent with to future completion requests; default false
        if not keep_context:
            self.reset_messages()

        # If the number of tokens in the system and assistant messages plus
        # the next interction (as calculated by `context_pair_length()`) will
        # exceed the token limit, remove the earliest 2 assistant messages.
        model = kwargs["model"]
        while (
            self.token_count(model)
            + self.context_pair_length(model, q=self.reserve_level)
            > MAX_TOKENS
        ):
            self.messages.remove(self.context[0])
            self.messages.remove(self.context[0])

        user_message = {"role": "user", "content": prompt}
        self.messages.append(user_message)
        kwargs["messages"] = self.messages
        try:
            if kwargs.get("stream"):
                response_chunks = []
                for chunk in openai.ChatCompletion.create(**kwargs):
                    try:
                        content = chunk["choices"][0]["delta"]["content"]
                    except KeyError:
                        # sometimes `delta` is missing `content`
                        continue
                    response_chunks.append(content)
                    yield content
                completion = "".join(response_chunks)
            else:
                response = openai.ChatCompletion.create(**kwargs)
                completion = response["choices"][0]["message"]["content"]
                yield completion
        except Exception:
            self.messages.pop()  # remove the unsuccessful user message
            raise
        else:
            self.messages.pop()  # remove the successful user message
            self.add_context(prompt, completion)

    def add_context(self, *contents):
        for content in contents:
            self.messages.append({"role": "assistant", "content": content})

    def token_count(self, model: str):
        return sum([count_tokens(m["content"], model) for m in self.messages])

    @property
    def context(self) -> list:
        return [m for m in self.messages if m["role"] == "assistant"]

    def context_pair_length(self, model: str, q: int = 50):
        """Return the q-th percentile of the lengths of past prompt-completion pairs."""
        context_lengths = [count_tokens(c["content"], model) for c in self.context]
        context_pair_lengths = (
            context_lengths[i] + context_lengths[i + 1]
            for i in range(0, len(context_lengths), 2)
        )
        return percentile(context_pair_lengths, q)


def count_tokens(s: str, model: str):
    """Return the number of tokens in string `s`."""
    if _TIKTOKEN_READY:
        encoding = tiktoken.encoding_for_model(model)
        encoded = encoding.encode(s)
        return len(encoded)
    else:
        # if not able to download tiktoken encodings:
        # use the estimate that 100 tokens correspond to 75 words
        # https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
        word_list = [w for w in re.split(r"\W", s)]
        return len(word_list) * 4 // 3


def percentile(data: typing.Iterable, q: int):
    sorted_data = sorted(data)
    if not sorted_data:
        return 0
    k = int((q / 100) * (len(sorted_data) - 1))
    return sorted_data[k]


def _test(args: argparse.Namespace):
    print(args)
    chat = Chat()
    if args.system_message:
        chat.system_message = args.system_message
    kwargs = dict(model=args.model, stream=args.stream)
    if args.temperature is not None:
        kwargs["temperature"] = args.temperature
    if args.top_p is not None:
        kwargs["top_p"] = args.top_p
    while True:
        try:
            prompt = input("\n> ")
        except KeyboardInterrupt:
            print("\n>>> session ended")
            return
        if prompt == "--reset":
            chat.reset_messages()
            print(">>> chat has been reset")
            continue
        print(">>>")
        for content in chat.send(prompt, keep_context=args.context, **kwargs):
            print(content, end="")
        print()


_argparser = argparse.ArgumentParser(prog="Chat")
_argparser.add_argument("--model", default="gpt-3.5-turbo")
_argparser.add_argument("--system-message")
_argparser.add_argument("--temperature", type=float)
_argparser.add_argument("--top-p", type=float)
_argparser.add_argument(
    "--context",
    default=True,
    action=argparse.BooleanOptionalAction,
)
_argparser.add_argument(
    "--stream",
    default=True,
    action=argparse.BooleanOptionalAction,
)

if __name__ == "__main__":
    _test(args=_argparser.parse_args())
