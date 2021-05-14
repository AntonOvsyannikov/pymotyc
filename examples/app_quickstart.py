""" Basic PyMotyc application.

This will show basic usage of PyMotyc:
    - declaration of pydantic model, to be used to statically type MongoDB collection.
    - declaration of the database, with statically typed collection,
    - creation of AsyncIOMotorClient and pymotyc.Engine instances and binding all things together,
    - storing model instances into database,
    - retrieving single and multiple model instances from the collection by id or with query,
    - modifying model instance by saving or document in-place,
    - deleting document from the database.

We have no field in the model to represent identity in this particular scenario, so Mongo's document
_id field of ObjectId type will be used as identity. To have the _id field in the returned model
instance we have to use inject_default_id = True option in correspondent methods.
This is just one strategy of identity management, supported by PyMotyc, see other examples for more.

To run this example it is necessary to have MongoDB up and running. You can use `./run.sh mongo`
to start MongoDB in Docker container on local host 127.0.0.1 on default port 27017.
If you have other settings please customize AsyncIOMotorClient creation.

"""
import asyncio

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

import pymotyc


# Create Pydantic model.
class Employee(BaseModel):
    name: str
    age: int


# Create database class with collection, annotated by Collection[] Generic, typed by Pydantic model.
class Warehouse:
    employees: pymotyc.Collection[Employee]


async def main():
    # Create Motor Client.
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")

    # Create PyMotyc engine instance, bind it to the Motor instance and provide the database to manage.
    await pymotyc.Engine().bind(motor=motor, databases=[Warehouse])

    # Drop collection just because this is example.
    # We have no custom indexes in the collection, otherwise they would have to be recreated here.
    await Warehouse.employees.collection.drop()

    # ===== Use statically typed collections! =====

    # Let's add first Employee to collection.
    vasya = await Warehouse.employees.save(Employee(name='Vasya Pupkin', age=42), inject_default_id=True)

    # Please note, that IDE correctly understand the type of returned model already, let's check it in run-time.
    assert isinstance(vasya, Employee)

    # Even there is no _id field in the model, the _id field of ObjectId type, which represents
    # document id provided by MongoDB, is injected thanks to inject_default_id=True option.
    assert hasattr(vasya, '_id')
    vasya_id = getattr(vasya, '_id')
    assert isinstance(vasya_id, ObjectId)

    # Let's add some more Employees.
    await Warehouse.employees.save(Employee(name='Frosya Taburetkina', age=22))
    await Warehouse.employees.save(Employee(name='Dusya Ivanova', age=20))

    # Let's explore our collection now...

    # ...as a whole
    employees = await Warehouse.employees.find(sort={'age': 1})
    assert employees == [
        Employee(name='Dusya Ivanova', age=20),
        Employee(name='Frosya Taburetkina', age=22),
        Employee(name='Vasya Pupkin', age=42)
    ]

    # ...or with query
    employees = await Warehouse.employees.find({'$and': [{'age': {'$gt': 40}}, {'name': {'$regex': 'Vasya'}}]})
    assert employees == [Employee(name='Vasya Pupkin', age=42)]

    # Let's get back our first Employee by it's identity.
    vasya = await Warehouse.employees.find_one(_id=vasya_id, inject_default_id=True)

    # Let's explore field's values, please note IDE hints for fields names.
    assert vasya.name == 'Vasya Pupkin'
    assert vasya.age == 42

    # If our application is single threaded and have no need of concurrency control
    # or we can ignore race conditions for some reason, the model instance can be
    # manipulated directly and saved back to the collection easily.
    # Due to injected _id engine knows, which document to update.
    # This approach is brilliant, cause it is migration-safe: even if Employee model
    # will be changed in future, all we have to do is to provide default values for new fields,
    # so they will be set to defaults while getting model form collection
    # and updated in the database while saving.
    vasya.age += 1
    vasya = await Warehouse.employees.save(vasya)
    assert vasya.age == 43

    # Alternatively we can use MongoDB update query to update the document in-place.
    # This should be considered carefully in migrations context, so defaults in model
    # to correspond Mongo's defaults for emply document fields.
    vasya = await Warehouse.employees.update_one(_id=vasya_id, update={'$inc': {'age': 1}})
    assert vasya.age == 44

    # Finally let's remove someone from collection.
    await Warehouse.employees.delete_one(_id=vasya_id)

    # And check if is it done.
    employees = await Warehouse.employees.find(sort={'age': 1})
    assert employees == [
        Employee(name='Dusya Ivanova', age=20),
        Employee(name='Frosya Taburetkina', age=22),
    ]


if __name__ == "__main__":
    asyncio.run(main())
