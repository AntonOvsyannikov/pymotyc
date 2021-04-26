import asyncio
from time import time
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

# import like this
from pymotyc import MotycModel, Engine, Collection


# ====================================================

class OrderHistoryItem(BaseModel):
    timestamp: int
    status: str


class Order(MotycModel):
    history: List[OrderHistoryItem] = []


# ====================================================


class Warehouse:
    orders: Collection[Order]


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    await Engine.create(Warehouse, motor=motor, inject_motyc_fields=True)
    await Warehouse.orders.collection.drop()

    order = await Warehouse.orders.save(Order())
    print(await Warehouse.orders.update(
        order,
        {"$push": {Order.history: OrderHistoryItem(timestamp=int(time()), status='processed')}}
    ))

    print("Everything fine!")


if __name__ == "__main__":
    asyncio.run(main())
