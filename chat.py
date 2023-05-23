import json

import openai

with open("gpt/keys.json", encoding="utf-8") as creds_file:
    creds = json.load(creds_file)

cred = creds[0]
openai.api_key = cred["key"]
openai.api_base = cred["base"]


class Chat:
    def __init__(self, system_message="You are a helpful assistant."):
        self.model = "gpt-3.5-turbo"
        self.messages = []
        self.system_message = system_message
        self.reset()

    def reset(self):
        self.messages = [{"role": "system", "content": self.system_message}]

    def send(self, prompt: str, *, assistant: bool = False, **kwargs):
        # `assistant`
        # if true, GPT responses are kept as assistant messages and
        # sent with to future completion requests; default false
        user_message = {"role": "user", "content": prompt}
        self.messages.append(user_message)
        try:
            response = openai.ChatCompletion.create(
                model=self.model, messages=self.messages, **kwargs
            )
        except Exception:
            self.messages.pop()  # remove the unsuccessful message
            raise
        if assistant:
            response_message = response["choices"][0]["message"]
            self.messages.append(response_message)
        else:
            self.reset()
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
            chat.reset()
            print(">>> chat has been reset")
            continue
        print(">>>")
        for content, finish_reason in chat.get_chunks(prompt):
            print(content, end=("\n" if finish_reason == "null" else ""))
        print()


if __name__ == "__main__":
    test()
