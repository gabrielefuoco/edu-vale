import pytest
from mongomock_motor import AsyncMongoMockClient
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
import os

# --- Setup Global Env Vars for Imports ---
os.environ["GROQ_API_KEY"] = "mock_key"
os.environ["MONGODB_URI"] = "mongodb://localhost"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:abc"

# --- Mock Telegram Objects ---

class FakeUser:
    def __init__(self, user_id=12345):
        self.id = user_id
        self.first_name = "UserTest"

class FakeChat:
    def __init__(self, chat_id=12345):
        self.id = chat_id

class FakeBot:
    async def send_message(self, chat_id, text, **kwargs):
        pass
        
    async def send_chat_action(self, *args, **kwargs):
        pass

class FakeMessage:
    def __init__(self, text, message_thread_id=None, user_id=12345):
        self.text = text
        self.message_thread_id = message_thread_id
        self.from_user = FakeUser(user_id)
        self.chat = FakeChat(user_id)
        self.voice = None
        self.bot = FakeBot()
        self.replies = []
        
    async def reply(self, text, **kwargs):
        self.replies.append({"text": text, "kwargs": kwargs})
        
    async def answer(self, text, **kwargs):
        self.replies.append({"text": text, "kwargs": kwargs})
        
    async def edit_text(self, text, **kwargs):
        self.replies.append({"text": text, "kwargs": kwargs})

class FakeCallbackQuery:
    def __init__(self, data, message: FakeMessage):
        self.data = data
        self.from_user = message.from_user
        self.message = message
        
    async def answer(self, text=None):
        pass

@pytest.fixture
def fake_msg_factory():
    def _create_message(text, thread_id=None, user_id=12345):
        return FakeMessage(text, thread_id, user_id)
    return _create_message

# --- Mock Database & Checkpointer ---

@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    mock_client = AsyncMongoMockClient()
    monkeypatch.setattr("database.connection.client", mock_client)
    return mock_client

@pytest.fixture(autouse=True)
def mock_checkpointer(monkeypatch):
    async def mock_get_checkpointer():
        return MemorySaver()
    monkeypatch.setattr("database.connection.get_checkpointer", mock_get_checkpointer)

# --- Mock LLM ---

mock_llm_responses = []

from tests.mock_llm_state import responses

class MockChatModel:
    def __init__(self, *args, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages, *args, **kwargs):
        if responses:
            return responses.pop(0)
        return AIMessage(content="Mock response")

@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setattr("agents.factory.ChatMistralAI", MockChatModel)
    responses.clear()

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test_key")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")

