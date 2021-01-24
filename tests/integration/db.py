from typing import Union

from pydantic import BaseModel
from typing_extensions import Literal

from pymotyc import Engine, Collection

engine = Engine()


class Employee(BaseModel):
    name: str
    age: int


class ProductBase(BaseModel):
    kind: str
    id: str = None


class Book(ProductBase):
    kind: Literal['book'] = 'book'
    pages: int


class Computer(ProductBase):
    kind: Literal['computer'] = 'computer'
    vendor: str


Product = Union[Book, Computer]


@engine.database
class Warehouse:
    empolyees: Collection[Employee]
    products: Collection[Product] = Collection(identity='id')


vasya = Employee(name='Vasya Pupkin', age=42)
frosya = Employee(name='Frosya Taburetkina', age=31)

book = Book(pages=42)
computer = Computer(vendor='Apple')
