""" Minimal PyMotyc application. """
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

import pymotyc
from pymotyc import M


class Employee(BaseModel):
    name: str
    age: int


class Warehouse:
    employees: pymotyc.Collection[Employee]


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    await pymotyc.Engine().bind(motor=motor, databases=[Warehouse], inject_motyc_fields=True)

    await Warehouse.employees.collection.drop()

    vasya = await Warehouse.employees.save(Employee(name='Vasya Pupkin', age=42))
    assert isinstance(vasya, Employee)

    employees = await Warehouse.employees.find({Employee.age: 42})
    assert employees == [Employee(name='Vasya Pupkin', age=42)]

    employees = await Warehouse.employees.find(M(Employee.age) == 42)
    assert employees == [Employee(name='Vasya Pupkin', age=42)]

    employees = await Warehouse.employees.find(M(Employee.name).regex('Vasya'))
    assert employees == [Employee(name='Vasya Pupkin', age=42)]

    employees = await Warehouse.employees.find(M(Employee.name).regex('Vasya') & M(Employee.age) == 42)
    assert employees == [Employee(name='Vasya Pupkin', age=42)]


if __name__ == "__main__":
    asyncio.run(main())
