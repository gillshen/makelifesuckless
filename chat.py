import dataclasses
import json
import re

import openai
import tiktoken

try:
    with open("keys.json", encoding="utf-8") as f:
        cred = json.load(f)
    openai.api_key = cred["key"]
    if "base" in cred:
        openai.api_base = cred["base"]
except FileNotFoundError:
    openai.api_key = openai.api_base = ""

try:
    tiktoken.get_encoding("cl100k_base")
    tiktoken.get_encoding("p50k_base")
    _TIKTOKEN_READY = True
except Exception:
    _TIKTOKEN_READY = False

_MAX_TOKENS = 4096


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
        self.reset_messages()

    def reset_messages(self):
        self.messages = [{"role": "system", "content": self.system_message}]

    def send(self, prompt: str, *, assistant: bool = False, **kwargs):
        # `assistant`:
        # if true, GPT responses are kept as assistant messages and
        # sent with to future completion requests; default false
        if not assistant:
            self.reset_messages()

        model = kwargs["model"]

        # First, count the number of messages and total tokens in self.messages:
        # if there are n messages with an average of t tokens per message
        # and t * (n + 2) is greater than the limit, then it is likely that the
        # next interaction will exceed the limit. As a precaution, remove the
        # earliest interaction (the earliest 2 assistant messages).
        while self.avg_token_count(model) * (self.message_count() + 2) > _MAX_TOKENS:
            past_interactions = [m for m in self.messages if m["role"] == "assistant"]
            self.messages.remove(past_interactions[0])
            self.messages.remove(past_interactions[1])

        user_message = {"role": "user", "content": prompt}
        self.messages.append(user_message)
        kwargs["messages"] = self.messages
        try:
            if kwargs.get("stream"):
                response_chunks = []
                for chunk in openai.ChatCompletion.create(**kwargs):
                    content = chunk["choices"][0]["delta"]["content"]
                    response_chunks.append(content)
                    yield content
                self.messages.append(
                    {"role": "assistant", "content": "".join(response_chunks)}
                )
            else:
                response = openai.ChatCompletion.create(**kwargs)
                response_message = response["choices"][0]["message"]
                self.messages.append(response_message)
                return response_message
        except Exception:
            self.messages.pop()  # remove the unsuccessful message
            raise

    def message_count(self):
        return len(self.messages)

    def total_token_count(self, model):
        return sum([count_tokens(m["content"], model) for m in self.messages])

    def avg_token_count(self, model):
        if self.messages:
            return self.total_token_count(model) / self.message_count()
        return 0


def count_tokens(s: str, model: str):
    """Return the number of tokens in string `s`"""
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


def test():
    chat = Chat()
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
        for content in chat.send(
            prompt, assistant=True, model="gpt-3.5-turbo", stream=True
        ):
            print(content, end="")
        print()


if __name__ == "__main__":
    test()
