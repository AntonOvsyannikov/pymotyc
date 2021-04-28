from typing import Union, List

from pydantic import BaseModel, Field, parse_obj_as
from typing_extensions import Literal

from pymotyc.util import camel_to_snake, get_annotations, py_dict


def test_camel_to_snake():
    assert camel_to_snake('CamelToSnake') == 'camel_to_snake'


def test_get_annotations():
    class A:
        x: int
        y = 1

    class B(A):
        z: float

    class C(B, A):
        z: str

    assert get_annotations(C) == {
        'x': int,
        'z': str
    }


class Model1(BaseModel):
    kind: Literal['Model1'] = 'Model1'
    foo: int


class Model2(BaseModel):
    kind: Literal['Model2'] = 'Model2'
    bar: str


Model = Union[Model1, Model2]
ModelList = List[Model]


def test_parse_obj_as():
    assert parse_obj_as(
        ModelList,
        [{'kind': 'Model1', 'foo': 1}, {'kind': 'Model2', 'bar': 'baz'}]
    ) == [Model1(foo=1), Model2(bar='baz')]

    assert parse_obj_as(
        ModelList,
        [Model1(foo=1), Model2(bar='baz')]
    ) == [Model1(foo=1), Model2(bar='baz')]


def test_py_dict():
    assert py_dict(
        ModelList,
        [Model1(foo=1), Model2(bar='baz')]
    ) == [{'kind': 'Model1', 'foo': 1}, {'kind': 'Model2', 'bar': 'baz'}]

    assert py_dict(
        ModelList,
        [{'kind': 'Model1', 'foo': 1}, {'kind': 'Model2', 'bar': 'baz'}]
    ) == [{'kind': 'Model1', 'foo': 1}, {'kind': 'Model2', 'bar': 'baz'}]


class Model3(BaseModel):
    id: int = Field(alias='_id')


def test_alias():
    assert parse_obj_as(Model3, {'_id': 1}) == Model3(_id=1)
    assert py_dict(Model3, Model3(_id=1)) == {'_id': 1}


class Model4(BaseModel):
    _foo: int = 1
    bar: int

    class Config:
        underscore_attrs_are_private = True


def test_private():
    m = parse_obj_as(Model4, {'bar': 1})
    assert m.bar == 1
    assert hasattr(m, '_foo')
    assert m._foo == 1


def test_pydict():
    assert py_dict(List[str], ['foo', 'bar']) == ['foo', 'bar']
    assert py_dict(List[int], ['1', '2']) == [1, 2]
    assert py_dict(dict, {'foo': 'bar'}) == {'foo': 'bar'}

    assert py_dict(List[Model1], [Model1(foo=1)]) == [{'kind': 'Model1', 'foo': 1}]
    assert py_dict(Union[Model1, Model2], Model1(foo=1)) == {'kind': 'Model1', 'foo': 1}

    # dictionary itself supported insted of models
    assert py_dict(Model1, {'kind': 'Model1', 'foo': 1}) == {'kind': 'Model1', 'foo': 1}


    # injected fields will be included, even if model have not declared it
    m = Model1(foo=1)
    object.__setattr__(m, '_id', 1)
    assert py_dict(Model1, m) == {'_id': 1, 'kind': 'Model1', 'foo': 1}
