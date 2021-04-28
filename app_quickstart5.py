import asyncio

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

import pymotyc
from pymotyc import M


class Employee(BaseModel):
    name: str
    age: int



# ----------------------------------------------------
engine = pymotyc.Engine()

@engine.database
class Warehouse:
    employees: pymotyc.Collection[Employee]


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")

    await engine.bind(motor=motor, inject_motyc_fields=True)

    await Warehouse.employees.collection.drop()

    await Warehouse.employees.save(Employee(name='Vasya Pupkin', age=42))
    await Warehouse.employees.save(Employee(name='Frosya Taburetkina', age=21))

    vasya = await Warehouse.employees.find_one({'age': 42}, inject_default_id=True)

    assert vasya.name == 'Vasya Pupkin'

    assert hasattr(vasya, '_id')

    vasya.age = 43
    await Warehouse.employees.save(vasya)

    employee = await Warehouse.employees.find_one({Employee.age: {"$eq": 21}})
    assert employee.name == "Frosya Taburetkina"

    employees = await Warehouse.employees.find(M(Employee.name).regex("Vasya") & (M(Employee.age) < 50))
    assert employees == [Employee(name='Vasya Pupkin', age=43)]

    print("Everything fine!")


if __name__ == "__main__":
    asyncio.run(main())
