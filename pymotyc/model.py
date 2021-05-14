from typing import TypeVar

from bson import ObjectId
from pydantic import BaseModel, Field

from pymotyc.collection import Collection
from pymotyc.query import MotycField

T = TypeVar('T')


class MotycModel(BaseModel):
    class Config:
        underscore_attrs_are_private = True

    _bound_collection: Collection = None

    async def save(self: T) -> T:
        assert self._bound_collection is not None, "No bound collection found, use Database.collection.save() first."
        return await self._bound_collection.save(self, mode='update')


class WithId(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: lambda oid: str(oid),
        }

    # Unfortunately, there is no way to name Pydantic model field as '_id', so alias to be used
    # It brings lot of confusion, but it's the only way. Fortunately it's almost always is under the hood.
    # So, one should use model.id and remember, that it's stored as '_id' in MongoDB.
    # Alternatively, _id field CAN be injected externally, so we can omit using id at all and always
    # use inject_default_id option in find... operations.
    id: ObjectId = Field(None, alias='_id')

class WithInjected(BaseModel):
    def __init_subclass__(cls, **kwargs):
        MotycField._inject_for_model(cls)
