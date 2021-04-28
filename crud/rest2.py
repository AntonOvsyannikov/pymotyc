"""
Simple REST API for CRUD operations, when identity is Mongo's ObjectId and is detached,
means _id field is not a part of the PyMotyc-managed model and will be injected with inject_default_id.

To keep things simple we use tuple as Out model and do conversion of ObjectId to str by hands.

EmployeeOut = Tuple[str, Employee]

Some BaseModel model can be used instead, see rest3.py for tips and tricks with model manipulations.

Also this scenario shows usage of unique indexes for non-identity fields.
"""

from typing import List, Tuple

from bson import ObjectId
from fastapi import FastAPI, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from pymongo import IndexModel
from pymongo.errors import DuplicateKeyError
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

import pymotyc


# ----------------------------------------------------

class Employee(BaseModel):
    login: str  # should be unique
    full_name: str
    age: int


EmployeeOut = Tuple[str, Employee]

# ----------------------------------------------------

engine = pymotyc.Engine()


@engine.database
class Warehouse:
    employees: pymotyc.Collection[Employee] = pymotyc.Collection(indexes=[IndexModel('login', unique=True)])


# ----------------------------------------------------

app = FastAPI(
    title='Warehouse',
    description='Simple Warehouse CRUD service for Employees, detached identity.',
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

@app.post('/employees', response_model=EmployeeOut, status_code=201)
async def create_employee(employee: Employee) -> EmployeeOut:
    """ Creates employee in database, login should be unique. """
    employee = await Warehouse.employees.save(employee, inject_default_id=True)
    return str(getattr(employee, '_id')), employee


@app.get('/employees', response_model=List[EmployeeOut])
async def list_employees() -> List[EmployeeOut]:
    """ Returns employees list from database ordered by login. """
    employees = await Warehouse.employees.find(sort={Employee.login: 1}, inject_default_id=True)
    return [
        (str(getattr(employee, '_id')), employee)
        for employee in employees
    ]


@app.get('/employees/{_id}', response_model=Employee)
async def get_employee(_id: str) -> Employee:
    """ Returns employee from database by it's id. """
    return await Warehouse.employees.find_one(_id=_id)


@app.put('/employees/{_id}', response_model=Employee)
async def put_employee(_id: str, employee: Employee) -> Employee:
    """ Updates employee completely in database by it's id. """
    return await Warehouse.employees.save(employee, _id=_id, mode='update')


@app.patch('/employees/{_id}', response_model=Employee)
async def patch_employee(_id: str, inc_age: int = Query(1)) -> Employee:
    """ Increments employee's age by given id. """
    return await Warehouse.employees.update_one(
        _id=_id,
        update={'$inc': {Employee.age: inc_age}}
    )


@app.delete('/employees/{_id}', status_code=204)
async def delete_employee(_id: str):
    """ Delete employee with given id from database. """
    await Warehouse.employees.delete_one(_id=_id)


if __name__ == "__main__":
    with TestClient(app) as cli:
        response = cli.post('/employees', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 201
        vasya_id, vasya = response.json()
        assert ObjectId(vasya_id)
        assert vasya == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.post('/employees', json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42})
        assert response.status_code == 400

        response = cli.post('/employees', json={'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20})
        assert response.status_code == 201
        frosya_id, frosya = response.json()
        assert ObjectId(frosya_id)
        assert frosya == {'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20}

        response = cli.get('/employees')
        assert response.status_code == 200
        assert response.json() == [
            [frosya_id, {'login': 'frosya', 'full_name': 'Frosya Taburetkina', 'age': 20}],
            [vasya_id, {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}]
        ]

        response = cli.get('/employees/' + vasya_id)
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 42}

        response = cli.put('/employees/' + vasya_id, json={'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43})
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

        response = cli.get('/employees/' + vasya_id)
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}

        response = cli.get('/employees/' + str(ObjectId()))
        assert response.status_code == 404

        response = cli.put('/employees/' + str(ObjectId()), json={'login': 'dusya', 'full_name': 'Dusya Ivanova', 'age': 22})
        assert response.status_code == 404

        response = cli.delete('/employees/' + frosya_id)
        assert response.status_code == 204

        response = cli.delete('/employees/' + frosya_id)
        assert response.status_code == 404

        response = cli.get('/employees')
        assert response.status_code == 200
        assert response.json() == [
            [vasya_id, {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 43}]
        ]

        response = cli.patch('/employees/' + vasya_id + '?inc_age=2')
        assert response.status_code == 200
        assert response.json() == {'login': 'vasya', 'full_name': 'Vasya Pupkin', 'age': 45}

        response = cli.patch('/employees/' + str(ObjectId()) + '?inc_age=2')
        assert response.status_code == 404

        print('Everything fine!')
