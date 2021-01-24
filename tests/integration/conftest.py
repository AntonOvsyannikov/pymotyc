import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from tests.integration import db


@pytest.fixture(autouse=True)
async def db_bound(loop):
    await db.engine.bind(motor=AsyncIOMotorClient("mongodb://127.0.0.1:27017"), already_bound='skip')
