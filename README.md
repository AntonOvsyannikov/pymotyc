# PyMotyc

Statically typed asynchronous MongoDB collections with [Pydantic](https://pydantic-docs.helpmanual.io/) models and [Motor](https://motor.readthedocs.io/) engine.

Motyc stands for **MO**ngodb **TY**ped **C**ollections, and also is diminutive for the word 'motocycle' in Russian, 
which, of course, also has a motor!

The library is designed to be a thin wrapper over Motor collections to bring static type 
checking over code-defined database schema.


## Example

```python
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
    # IDE already knows there, that vasya is of Employee type
    
    assert isinstance(vasya, Employee) 

    employees = await Warehouse.employees.find()
    assert employees == [Employee(name='Vasya Pupkin', age=42)]


if __name__ == "__main__":
    asyncio.run(main())

```

## Installation

```
pip install pymotyc
```

## Features

Main idea of the library is to use Pydantic models to statically type MongoDB collections 
to automate parsing documents from collection to models instances (and vise versa) and also
enable static type checking for saved and retrieved objects, which brings handy IDE support 
for attributes access etc.

- Declarative MongoDB databases with statically typed (by Pydantic models) collections 
  with `save`, `find`, `find_one`, `update` built-in methods and a bunch of utility methods 
  to deal with raw Motor collections.

  
- One collection can be typed with Discriminated Union to hold different documents corresponded 
  to several models. Retrieved documents will be converted to correct model classes instances  
  thanks to Pydantic.

  
- Automation of routine procedures for collections management, like indexes creation.


- Flexible identity management of documents in the collection:
    * MongoDB's `_id` field injection to model, even if it has no one (detached id),
    * id field of type `bson.ObjectId` (with `alias='_id'`, limitation of Pydantic), which represents MongoDB's _id field 
      (the model should be properly configured or inherited from `pymotyc.WithId` trait),
    * auto-generation of identity with callable provided (uuid in str representation by default, actually this is the most convenient method),
    * client-managed identity field, index is created to guaranty identity uniques. 


- `pymotyc.MotycModel` base class (and `pymotyc.WithId` trait) to hold relation of the model instance with
  collection it was retrieved from, this allows to modify model instance and call `save` directly on 
  instance itself.

  
- Direct access to Motor's collection, which allows to rely on original MongoDB API and then use typed
  collection utility methods to parse retrieved documents to model instances.

### Experimental

Another part of PyMotyc is so-called *refactorable queries*. The idea is when you type the query like

```python
await collection.find({'foo': 'bar'})
```

you have no relation between key 'foo' in the dict and model's (with which collection is typed) field `foo`,
so when you rename field IDE have no idea, in which queries this field is used.

PyMotyc allows to use model's fields as keys in queries in built-in typed collection methods.

To enable this feature one should use `inject_motyc_fields=True` in `Engine.bind` method, 
so query in example above can be re-written like this:

```python
    ...
    await pymotyc.Engine().bind(motor=motor, databases=[Warehouse], inject_motyc_fields=True)
    ...
    employees = await Warehouse.employees.find({Employee.age: 42})
    assert employees == [Employee(name='Vasya Pupkin', age=42)]
```

Now one can rename model's field `age` with refactor feature of the IDE and IDE automatically 
will rename keys in correspondent queries! Also, one can click on `age` field and see all usages in queries. 

For this feature PyMotyc uses dirty trick, that's why feature should be considered as experimental. 

Using the fact, that Pydantic already initialized all its internal structures during model class creation, 
PyMotyc replaces model's class attributes with `pymotyc.MotycField` class instances, which holds 
all necessary field's info like name alias etc, and then parses queries, searching for MotycField in them.

PyMotyc also have simple query builder. One can use `MotycField`s in logical expressions, as well as use
methods like `regexp` directly on them. This will form MotycQuery as result, which then will be converted
to MongoDB query by PyMotyc. To use models fields with injected `MotycField`s in logical expression
they should be cast to `MotycField` explicitly to calm down the IDE. One can use `pymotyc.M` helper for this.

```python
    employees = await Warehouse.employees.find(M(Employee.name).regex('Vasya') & M(Employee.age) == 42)
    assert employees == [Employee(name='Vasya Pupkin', age=42)]
```

## Further reading

Documentation of the library is provided in *learn-by-example* format. 
One can find detailed comments in the examples below, which covers all aspects of PyMotyc usage.

To run examples, it is necessary to have MongoDB up and running. You can use `./run.sh mongo`
to start MongoDB in Docker container on local host 127.0.0.1 on default port 27017 
(Docker should be [installed](https://docs.docker.com/engine/install/) first of course). 
If you have other settings please customize AsyncIOMotorClient creation.


- [app_quickstart.py](examples/app_quickstart.py) will show basic usage of PyMotyc:
    - declaration of pydantic model, to be used to statically type MongoDB collection.
    - declaration of the database, with statically typed collection,
    - creation of AsyncIOMotorClient and pymotyc.Engine instances and binding all things together,
    - storing model instances into database,
    - retrieving single and multiple model instances from the collection by id or with query,
    - modifying model instance by saving or document in-place,
    - deleting document from the database.


- [app_quickstart2.py](examples/app_quickstart2.py) will show some more concepts:
    - declarative binding of the database to pymotyc.Engine instance with `@engine.database` decorator,
    - custom identity field, id will be generated by PyMotyc,
    - inject_motyc_fields=True options to turn model fields to MotycField,
    - model fields (turned to MotycField) then can be used as keys in queries, making them refactorable,
    - query builder, when logical operations between MotycField will form MotycQuery,
      which can be used then in collection find... operations.
      

- [app_quickstart3.py](examples/app_quickstart3.py) tries to reproduce more or less real usage scenario:
    - MotycModel as a base to have id model field, which represents _id document field of ObjectId type,
    - many models with related ones,
    - discriminated unions of models to store in one collection,
    - collections of related models,
    - different strategies of identity management,
    - complex search and update queries.

  
- [rest_api](examples/rest_api) demonstrates several REST API applications, based on [FastAPI](https://fastapi.tiangolo.com/),
  together with PyMotyc, which are differs by identity management strategies. 
