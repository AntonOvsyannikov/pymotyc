""" Simple Pymotic application, which demonstrate key features:
    - statically typed collections with Pydantic Models in declarative database class,
    - saving Model to collection,
    - ordinary MongoDB queries to find docs and parse them to models,
    - _id field injection to have binding with doc in database for saving changes,
    - refactorable queries, where Model fields can be used as keys in MongoDB queries to have relation
        between Models and queries, in whith they are used,
    - simple Query builder for operations like >=, and, regex.

For more features like
    - several collection in database,
    - different Models in same collection,
    - custom id management,
please see app_quickstart2.py
"""
import asyncio

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

import pymotyc
from pymotyc import M


# ----------------------------------------------------
# Create Pydantic model.

class Employee(BaseModel):
    name: str
    age: int


# ----------------------------------------------------
# Create PyMotyc engine instance.

engine = pymotyc.Engine()


# ----------------------------------------------------
# Create database class with collections, annotated by Collection[] Generic.
# Put it under control of Motyc engine with @engine.database decorator.

@engine.database
class Warehouse:
    empolyees: pymotyc.Collection[Employee]


async def main():
    # ----------------------------------------------------
    # Create Motor Client. Provide mongo_host, port etc there.
    # You can use ./run.sh mongo to start MongoDB in Docker container locally with this settings.
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")

    # ----------------------------------------------------
    # Bind PyMotyc Engine instance to the Motor instance.
    # Use inject_motyc_fields=True to safely modify Employee model to support refactorable queries.
    await engine.bind(motor=motor, inject_motyc_fields=True)

    # ----------------------------------------------------
    # Drop collection through the link to original Motor collection to reproduce results.
    await Warehouse.empolyees.collection.drop()

    # ====================================================
    # Use statically typed collections!
    # ====================================================

    # Let add several Employee to the collection.
    await Warehouse.empolyees.save(Employee(name='Vasya Pupkin', age=42))
    await Warehouse.empolyees.save(Employee(name='Frosya Taburetkina', age=21))

    # Let find one by age to modify, for this we need to inject _id field to responce model.
    vasya = await Warehouse.empolyees.find_one({'age': 42}, inject_default_id=True)

    # vasya's type is Employee now (inferred from Collection[] annotation), enjoy ide type hints!
    assert vasya.name == 'Vasya Pupkin'

    # This is identity field, injected by PyMotyc, even if there is no in the Model.
    assert hasattr(vasya, '_id')

    # We can modify and save model now, thanks to _id field injected by PyMotyc.
    vasya.age = 43
    await Warehouse.empolyees.save(vasya)

    # Let query database. We can use Employee fields as a key in queries, thanks to PyMotyc.
    employee = await Warehouse.empolyees.find_one({Employee.age: {"$eq": 21}})
    assert employee.name == "Frosya Taburetkina"

    # We can also use simple query builder, built in PyMotyc.
    # M helper is used just to cast injected into Model fields to MotycField to satisfy typechecker.
    employees = await Warehouse.empolyees.find(M(Employee.name).regex("Vasya") & (M(Employee.age) < 50))
    assert employees == [Employee(name='Vasya Pupkin', age=43)]

    print("Everything fine!")


if __name__ == "__main__":
    asyncio.run(main())
