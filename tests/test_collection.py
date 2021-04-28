from typing import Union

import pytest
from pydantic import BaseModel
from typing_extensions import Literal

from pymotyc import Collection, Engine


class Model(BaseModel):
    foo: int
    bar: str


class SomeDatabase:
    collection_foo: Collection[Model]
    collection_bar: Collection[Model] = Collection(name='some_collection')


class MockMotorCollection:
    def __init__(self, name, db: 'MockMotorDB'):
        self.name = name
        self.db = db


class MockMotorDB:
    def __init__(self, name):
        self.name = name

    def __getattr__(self, item):
        return MockMotorCollection(item, self)


class MockMotor:
    def __getattr__(self, item):
        return MockMotorDB(item)


async def test_binding():
    Engine.create(motor=MockMotor(), databases=[SomeDatabase])

    assert SomeDatabase.collection_foo.db.name == 'some_database'

    c = SomeDatabase.collection_foo.collection
    assert isinstance(c, MockMotorCollection)
    assert c.name == 'collection_foo'
    assert c.db.name == 'some_database'

    c = SomeDatabase.collection_bar.collection
    assert isinstance(c, MockMotorCollection)
    assert c.name == 'some_collection'
    assert c.db.name == 'some_database'


class Database:
    foo: Collection[Model]
    bar: Collection[dict]


async def test_parse_document():
    Engine.create(motor=MockMotor(), databases=[Database])

    model = Database.foo.parse_document({'foo': 1, 'bar': 'baz'})
    assert isinstance(model, Model)
    assert model == Model(foo=1, bar='baz')

    model = Database.bar.parse_document({'foo': 1, 'bar': 'baz'})
    assert isinstance(model, dict)
    assert model == {'foo': 1, 'bar': 'baz'}


def test_check_type_get_basemodels():
    class ProductBase(BaseModel):
        kind: str

    class Book(ProductBase):
        kind: Literal['book'] = 'book'

    class Computer(ProductBase):
        kind: Literal['computer'] = 'computer'

    Product = Union[Book, Computer]

    assert Collection._check_type_get_basemodels(ProductBase) == [ProductBase]
    assert Collection._check_type_get_basemodels(Book) == [Book, ProductBase]
    assert Collection._check_type_get_basemodels(Product) == [Book, Computer, ProductBase]

    with pytest.raises(TypeError):
        Collection._check_type_get_basemodels(int)
