import json
import dataclasses

import openai

try:
    with open("keys.json", encoding="utf-8") as f:
        cred = json.load(f)
    openai.api_key = cred["key"]
    openai.api_base = cred["base"]
except FileNotFoundError:
    openai.api_key = openai.api_base = ""


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
        # `assistant`
        # if true, GPT responses are kept as assistant messages and
        # sent with to future completion requests; default false
        user_message = {"role": "user", "content": prompt}
        self.messages.append(user_message)
        kwargs["messages"] = self.messages
        try:
            response = openai.ChatCompletion.create(**kwargs)
        except Exception:
            self.messages.pop()  # remove the unsuccessful message
            raise
        if assistant:
            response_message = response["choices"][0]["message"]
            self.messages.append(response_message)
        else:
            self.reset_messages()
        return response

    def get_chunks(self, prompt: str, *, assistant: bool = False, **kwargs):
        kwargs["stream"] = True
        response = self.send(prompt, assistant=assistant, **kwargs)
        for chunk in response:
            choice_0 = chunk["choices"][0]
            content = choice_0["delta"]["content"]
            finish_reason = choice_0["finish_reason"]
            yield content, finish_reason


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
        for content, finish_reason in chat.get_chunks(prompt):
            print(content, end=("\n" if finish_reason == "null" else ""))
        print()


if __name__ == "__main__":
    test()
