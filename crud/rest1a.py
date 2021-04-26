"""
Simple REST API for CRUD operations, when identity is managed completely on client side,
so resource id is part of the model and id management of any kind on database side is not necessary.

Here we use PUT both to create and modify resource, return 200 or 201 depending on resource created or modified.
This shows usage of __created__ injected field.

"""

from typing import List

from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError
from starlette.responses import JSONResponse, Response
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

@app.put('/employees/{login}', response_model=Employee)
async def put_employee(login: str, employee: Employee, response: Response) -> Employee:
    """ Creates or modifies employee. """
    if login != employee.login:
        raise HTTPException(status_code=400, detail='Login can not be modified.')
    employee = await Warehouse.employees.save(employee, inject_created=True)
    if getattr(employee, '__created__'): response.status_code = 201
    return employee


@app.get('/employees', response_model=List[Employee])
async def list_employees() -> List[Employee]:
    """ Returns employees list from database ordered by login. """
    return await Warehouse.employees.find(sort={Employee.login: 1})


@app.get('/employees/{login}', response_model=Employee)
async def get_employee(login: str) -> Employee:
    """ Returns employee from database by it's login. """
    return await Warehouse.employees.find_one({Employee.login: login})


@app.patch('/employees/{login}', response_model=Employee)
async def patch_employee(login: str, inc_age: int = Query(1)) -> Employee:
    """ Increments employee's age by given login. """

    return await Warehouse.employees.update_one(
        {Employee.login: login},
        update={'$inc': {Employee.age: inc_age}}
    )


@app.delete('/employees/{login}', status_code=204)
async def delete_employee(login: str):
    """ Delete employee with given login from database. """
    await Warehouse.employees.delete_one({Employee.login: login})


if __name__ == "__main__":
    with TestClient(app) as cli:
        response = cli.put('/employees/vasya', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 201
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.put('/employees/vasya', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.put('/employees/frosya', json={'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20})
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

        response = cli.get('/employees/dusya')
        assert response.status_code == 404

        response = cli.put('/employees/vasya', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43})
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

        response = cli.get('/employees/vasya')
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

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

        print('Everything fine!')
