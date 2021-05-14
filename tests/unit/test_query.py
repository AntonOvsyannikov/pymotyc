from typing import cast

from pydantic import Field

from pymotyc.model import MotycModel, WithInjected
from pymotyc.query import MotycQuery, MotycField


class Model(WithInjected):
    foo: int
    bar: int = Field(None, alias='bar_alias')


def test_injected():
    # Model.foo injected as MotycField by MotycModel.__init_subclass__
    assert isinstance(Model.foo, MotycField)


def test_query_builder_for_motyc_model():
    query: MotycQuery

    query = cast(MotycQuery, (
            (Model.foo == 1) &
            (Model.foo > 1) &
            (Model.foo < 1) &
            (Model.foo >= 1) &
            (Model.foo <= 1) &
            (Model.foo != 1)
    ))

    assert str(query) == '(((((foo==1 AND foo>1) AND foo<1) AND foo>=1) AND foo<=1) AND foo!=1)'

    query = cast(MotycQuery, (
            (Model.foo == 1) &
            (Model.foo == 2) |
            (Model.foo == 3)
    ))
    assert str(query) == '((foo==1 AND foo==2) OR foo==3)'
    assert query.to_mongo_query() == \
           {'$or': [{'$and': [{'foo': {'$eq': 1}}, {'foo': {'$eq': 2}}]}, {'foo': {'$eq': 3}}]}


def test_build_query_from_motyc_fields():
    assert MotycQuery.build_mongo_query(
        {'$and': [{Model.foo: {'$eq': 1}}, {Model.bar: {'$eq': 2}}]}
    ) == {'$and': [{'foo': {'$eq': 1}}, {'bar_alias': {'$eq': 2}}]}
