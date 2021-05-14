"""
Simple REST API for CRUD operations, when identity is managed completely on client side, so 
resource id is part of the model and id management of any kind on database or PyMotyc side is not necessary.

Here we use POST to create resource and PUT only to modify known one.
"""

from typing import List

from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

import pymotyc


# ----------------------------------------------------

class Employee(BaseModel):
    login: str  # should be unique and is used as id
    full_name: str
    age: int


# ----------------------------------------------------

engine = pymotyc.Engine()


@engine.database
class Warehouse:
    employees: pymotyc.Collection[Employee] = pymotyc.Collection(identity='login')


# ----------------------------------------------------

app = FastAPI(
    title='Warehouse',
    description='Simple Warehouse CRUD service for Employees, client-managed identity.',
    version="0.1.0",
)


@app.on_event("startup")
async def init_app():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    await engine.bind(motor=motor, inject_motyc_fields=True)
    await Warehouse.employees.collection.drop()
    await Warehouse.employees.create_indexes()


# ----------------------------------------------------

@app.exception_handler(pymotyc.errors.NotFound)
async def not_found(_request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(DuplicateKeyError)
async def exists_or_constrain_violation(_request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


# ----------------------------------------------------

@app.post('/employees', response_model=Employee, status_code=201)
async def create_employee(employee: Employee) -> Employee:
    """ Creates employee in database, login is mandatory and should be unique. """
    return await Warehouse.employees.save(employee, mode='insert')


@app.get('/employees', response_model=List[Employee])
async def list_employees() -> List[Employee]:
    """ Returns employees list from database ordered by login. """
    return await Warehouse.employees.find(sort={Employee.login: 1})


@app.get('/employees/{login}', response_model=Employee)
async def get_employee(login: str) -> Employee:
    """ Returns employee from database by it's login. """
    return await Warehouse.employees.find_one({Employee.login: login})


@app.put('/employees/{login}', response_model=Employee)
async def put_employee(login: str, employee: Employee) -> Employee:
    """ Updates employee completely in database by given login.
    Login itself can not be modified.
    """
    if login != employee.login:
        raise HTTPException(status_code=400, detail='Login can not be modified.')
    return await Warehouse.employees.save(employee, mode='update')


@app.patch('/employees/{login}', response_model=Employee)
async def patch_employee(login: str, inc_age: int = Query(1)) -> Employee:
    """ Increments employee's age by given login. """

    # That's the key disadvantage of the library.
    # We can't just get model from db, increment age and save it back unfortunately,
    # because of race conditions, we need to obtain document lock somehow,
    # but it's not supported by MongoDB directly.
    # https://stackoverflow.com/questions/11076272/its-not-possible-to-lock-a-mongodb-document-what-if-i-need-to
    # https://www.mongodb.com/blog/post/how-to-select--for-update-inside-mongodb-transactions
    # https://jimmybogard.com/document-level-pessimistic-concurrency-in-mongodb-now-with-intent-locks/
    # Instead we must use MongoDB API (or MotycQuery builder) to manipulate fields directly,
    # but this is not migration-safe (cause the document in the collection can have old version
    # without field to update).
    # Author still in search of better solution.

    return await Warehouse.employees.update_one(
        {Employee.login: login},
        update={'$inc': {Employee.age: inc_age}}
    )


@app.delete('/employees/{login}', status_code=204)
async def delete_employee(login: str):
    """ Delete employee with given login from database. """
    await Warehouse.employees.delete_one({Employee.login: login})

    # or
    # employee = await Warehouse.employees.find_one({Employee.login: login})
    # await Warehouse.employees.detach(employee)


if __name__ == "__main__":
    with TestClient(app) as cli:
        response = cli.post('/employees', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 201
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.post('/employees', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 400

        response = cli.post('/employees', json={'full_name': 'Vasya Pupkin', 'age': 42})  # Login is mandatory
        assert response.status_code == 422

        response = cli.post('/employees', json={'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20})
        assert response.status_code == 201
        assert response.json() == {'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20}

        response = cli.get('/employees')
        assert response.status_code == 200
        assert response.json() == [
            {'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20},
            {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}
        ]

        response = cli.get('/employees/vasya')
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.put('/employees/vasya', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43})
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

        response = cli.get('/employees/vasya')
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

        response = cli.get('/employees/dusya')
        assert response.status_code == 404

        response = cli.put('/employees/dusya', json={'login': 'dusya', 'full_name': 'Dusya Ivanova', 'age': 22})
        assert response.status_code == 404

        response = cli.delete('/employees/frosya')
        assert response.status_code == 204

        response = cli.delete('/employees/frosya')
        assert response.status_code == 404

        response = cli.get('/employees')
        assert response.status_code == 200
        assert response.json() == [
            {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}
        ]

        response = cli.patch('/employees/vasya?inc_age=2')
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 45}

        response = cli.patch('/employees/dusya?inc_age=2')
        assert response.status_code == 404
