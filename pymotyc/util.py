import inspect

import re
from typing import Dict, Any, TypeVar, Generic, Type

from pydantic import validate_arguments, BaseModel


def camel_to_snake(s):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()


def get_annotations(cls: type) -> Dict[str, Any]:
    result = {}
    for cls in reversed(inspect.getmro(cls)):
        result.update(getattr(cls, '__annotations__', {}))
    return result


T = TypeVar('T')

# replaced by parse_obj_as
# def py_model(t: Type[T], d) -> T:
#     """ Makes Pydantic model or thier collection from dict or thier collection, using model type or Generic based on it.
#     :param t: Pydantic BaseModel or Generic based on it, like Union, List etc, can include nested items.
#     :param d: Dictionary or collection, correspondent to t, i.e. if t is List[Model] we expect List[dict].
#         You can also use Pydantic model in mixture with dicts.
#     :return: Pydantic model or it's collection, correnpondent to t provided.
#     """
#
#     def fabric():
#         def f(x):
#             return x
#
#         f.__annotations__['x'] = t
#         return validate_arguments(f)
#
#     f = fabric()
#     return f(d)


def py_dict(t, m):
    """ Makes dict or theier collection from Pydantic model or thier collection.
    This is opposite to py_model: py_dict(T, py_model(T, d)) === d
    :param t: Pydantic BaseModel or Generic based on it, like Union, List etc, can include nested items.
    :param m: Pydantic model or it's collection, should correspond to t.
        You can also use dicts in mixture with models, they will be parsed into models first.
    :return: Dict or it's collection, correspondant to t provided.
    """
    class Model(BaseModel):
        f: t

    model = Model(f=m)

    return model.dict(by_alias=True)['f']

