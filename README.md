# PyMotyc

Statically typed asynchronous MongoDB collections with Pydantic models and Motor engine.

Motyc stands for MOngodb TYped Collections, and also is diminutive for the word 'motocycle' in Russian, 
which is known to have a Motor of course!

## Key features

- Daclarative MongoDB databases with statically typed collections (by Pydantic models). 

<details>
  <summary>Example</summary>

```
class Employee(BaseModel):
    name: str
    age: int

engine = pymotyc.Engine()

@engine.database
class Warehouse:
    empolyees: pymotyc.Collection[Employee]
  ```
  
</details>

- Statically typed MongoDB collections with `find`, `find_one`, `save` and `update` capabiilities. 

- Ability to use your model's fields as keys in ordinary MongoDB queries to have relation between model's fields and queries, in which they are used.
as well as advaced query builder with logical expresisons over models fields.
- Flexible identity management during save operation, wherer...
- .


One can use original Pydantic models, or inherit them from `MotycModel` which is no more than well configured BaseModel) 
to have features like default identity management with id field and methods directly on model instance to save it to bound collection 


Also, it's possible to fall back to raw Motor collections and cursor management, 
but use utility API to build queries and parse returned documents.
  

## Installation

```
pip install pymotyc
```

## Quickstart

Please explore this minimal, but fully functional [application](app/app_quickstart.py).


Do import stuff.
```
import asyncio
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import pymotyc
```

Create Pydantic model.

```
class Employee(BaseModel):
    name: str
    age: int
```


Create database class with collections, annotated by Collection[] Generic.  

```
class Warehouse:
    empolyees: pymotyc.Collection[Employee]
```

Create Motor Client.
Provide mongo_host, port etc there. We assume mongo is running on local host with default port.
You can use `./run.sh mongo` to start MongoDB instance in docker container.

```
async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
```

Create PyMotyc Engine.
Provide Motor client and list of databases to manage by this engine.
Engine will create (if no) Collection instanses inside database classes, looking for Collection[] annotaions.

```
    await pymotyc.Engine.create(motor=motor, databases=[Warehouse])
```

Now you can access raw Motor collection and db through correspondent attributes of Collection instances.
There we will just drop collection to reproduce results of the app runs.

```
    await Warehouse.empolyees.collection.drop()
```

Now you can use statically typed collections!

```
    await Warehouse.empolyees.save(Employee(name='Vasya Pupkin', age=42))

    vasya = await Warehouse.empolyees.find_one(age=42)

    # vasya type is Employee now, enjoy ide type hints!
    assert vasya.name == 'Vasya Pupkin'

    employees = await Warehouse.empolyees.find(age=42)
    assert employees == [Employee(name='Vasya Pupkin', age=42)]
```

The problem now is, that model instances have no relation with documents inside database,
so we can't modify saved or fetched documents in database. To solve this we should provide
id management capabilities, see next step!


## Go deeper

### Models hierarchy and migrations 
### Id fields and indexes
### Raw queries and iterators
### Refactorable queries

Discriminated Unionsi s killing feature both of pydantic and pymotic, so we can keep 
different models in one collection and pymotyc will be able to parse it to correct class instances.

See different REST API designs.