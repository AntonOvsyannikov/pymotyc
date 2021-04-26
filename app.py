import asyncio

from motor.core import AgnosticCollection
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")

    col: AgnosticCollection = motor.db.collection

    await col.drop()
    await col.insert_one({'foo': 1, 'bar': 1})
    await col.update_one({'foo': 2}, {'$set': {'bar': 2}})
    await col.delete_one({'foo': 2})

    print(await col.find({}).to_list(1000))

    print("Everything fine!")


if __name__ == "__main__":
    asyncio.run(main())
