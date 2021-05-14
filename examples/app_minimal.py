""" Minimal PyMotyc application. """
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

import pymotyc


class Employee(BaseModel):
    name: str
    age: int


class Warehouse:
    employees: pymotyc.Collection[Employee]


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    await pymotyc.Engine().bind(motor=motor, databases=[Warehouse])

    await Warehouse.employees.collection.drop()

    vasya = await Warehouse.employees.save(Employee(name='Vasya Pupkin', age=42))
    assert isinstance(vasya, Employee)

    employees = await Warehouse.employees.find()
    assert employees == [Employee(name='Vasya Pupkin', age=42)]


if __name__ == "__main__":
    asyncio.run(main())
