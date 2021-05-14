import inspect

import re
from typing import Dict, Any


def camel_to_snake(s):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()


def get_annotations(cls: type) -> Dict[str, Any]:
    result = {}
    for cls in reversed(inspect.getmro(cls)):
        result.update(getattr(cls, '__annotations__', {}))
    return result


