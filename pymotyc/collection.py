from typing import TypeVar, Generic, List, Optional, Union, Type, Iterable, Callable, cast
from uuid import uuid4

import typing_inspect
from bson import ObjectId
from motor.core import AgnosticCollection, AgnosticDatabase, AgnosticCursor
from pydantic import parse_obj_as, BaseModel
from pymongo import IndexModel, ReturnDocument
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from typing_extensions import Literal

from pymotyc import Engine
from pymotyc.errors import NotFound
from pymotyc.query import MotycQuery, MotycField

T = TypeVar('T', bound=BaseModel)


class Collection(Generic[T]):
    # Motor collection.
    collection: AgnosticCollection

    # Motor database.
    db: AgnosticDatabase

    # Type of the collection, should be BaseModel or Union of them.
    t: type

    # ----------------------------------------------------
    # Main API

    def __init__(
            self,
            *,
            name: Optional[str] = None,
            identity: str = '_id',
            indexes: Iterable[Union[str, IndexModel]] = (),
            id_generator: Callable = lambda: str(uuid4())
    ):
        """ Initializes Collection instance.

        :param name: Collection name.
            If None will be set during engine binding to name of the
            attribute of database class.

        :param identity: Document's field name, which represents identity, default is Mongo's _id.
            See save() method for details of identity management.

        :param indexes: Indexes to create for collection.
            For non-default identity field, unique index is always created.
            To create additional NON unique indexes just put field names into the list.
            To fine tune index creation (i.e. make them unique) use IndexModel instead.

            Indexes are created during collection binding, so if collection dropped after that,
            indexes should be re-recreated manually by calling Collection.create_indexes().

        :param id_generator: Callable to generate ids for non-default identity management (see save()).
        """
        self.name = name
        self.identity = identity
        self.indexes = indexes
        self.id_generator = id_generator

    async def save(
            self, item: T, *,
            _id=None,
            mode: Literal['save', 'insert', 'update'] = 'save',
            inject_default_id: bool = False,
            inject_created: bool = False

    ) -> T:
        """ Saves, inserts or updates model instance to the collection.

        :param item: Model instance to save.

        :param mode: Save mode, should be one of:
            'save' (default):
                - If no identity field is provided, the document is considered as new
                    and is always INSERTED, while it's identity is generated:
                        - by database while inserting, if collection's identity is default ('_id'),
                        - by callable provided during collection creation otherwise.

                    Can raise pymongo.errors.DuplicateKeyError if callable generated
                    not unique identity value by some reason.

                - If identity is provided, the document is considered as (may be) existing
                    and in need of updating, so it is UPSERTED into collection based on
                    it's identity field.

                The mode is migration safe and useful in non-concurrent applications,
                where we can safely get model from collection (possibly old versioned,
                defaults must be provided for new fields in the model), modify it in
                python code and save back to the collection.
                In concurrent applications document lock should be obtained somehow.

            'insert':
                Tries to INSERT new document to the collection, identity must be provided.

                Raises pymongo.errors.DuplicateKeyError if document already exists
                cause unique index is created for identity field during collection binding
                (do not forget to recreate indexes if you manually drops collection).

                The mode is useful to check, that is no document exists with provided identity.
                Identity most probably is non default in that case.

            'update':
                Tries to UPDATE existing document in the collection, identity must be provided.

                Raises NotFound if no document found to update.

                Please note, despite the name of the mode 'update' the target document
                will be overwritten as a whole.

                The mode is useful to make sure the document with provided identity
                exists in the collection.

            In any case, when identity for collection is non default (not an '_id'),
            the _id field (or field with '_id' alias) should NOT be present
            in the model, cause it can not be returned correctly in some scenarios.
            For same reason inject_default_id should be False.

        :param _id: Mongo's _id for the document to save, will be converted to ObjectId.

            To be provided only if collection's identity is '_id' and instance itself
            DOES NOT contain _id nor from model nor injected.

        :param inject_default_id: Should _id field be injected into returned model
            in case when no field with '_id' alias exists in the model.

        :param inject_created: Should __created__ field be injected into returned model.

        :return: Model instance after saving, including id generated or injected.
        """
        document = item.dict(by_alias=True)

        if self.identity != '_id':
            assert '_id' not in document, "Should not have _id in the instance if collection's identity is non default."

        if _id is not None:
            assert self.identity == '_id', "_id parameter can be provided only if collection's identity is default."
            assert '_id' not in document, "_id should be provided ether in instance or by _id param."
            document['_id'] = ObjectId(_id)

        if mode == 'save':
            if document.get(self.identity) is None:  # === New document.
                if self.identity == '_id':
                    if '_id' in document: del document['_id']
                else:
                    document[self.identity] = self.generate_id()

                result: InsertOneResult = await self.collection.insert_one(document)  # will fail if exists due to index=unique violation for identity
                document['_id'] = result.inserted_id  # will be removed while back-parsing if not necessary
                document['__created__'] = True

            else:  # == Possibly an existing document that needs to be updated.
                result: UpdateResult = await self.collection.update_one(
                    {self.identity: document[self.identity]},
                    {'$set': document}, upsert=True
                )
                if result.upserted_id is not None:
                    document['_id'] = result.upserted_id
                    document['__created__'] = True

        elif mode == 'insert':
            assert document.get(self.identity) is not None, f"Need identity ({self.identity}) for insert mode, use save mode to insert document without identity."
            _result: InsertOneResult = await self.collection.insert_one(document)
            document['__created__'] = True

        elif mode == 'update':
            assert document.get(self.identity) is not None, f"Need identity ({self.identity}) for update mode."
            mongo_query = {self.identity: document[self.identity]}
            result: UpdateResult = await self.collection.update_one(
                mongo_query,
                {'$set': document}
            )
            if not result.matched_count: raise NotFound(mongo_query)

        else:
            assert False, f"Mode {mode} is not supported."

        return self.parse_document(document, inject_default_id=inject_default_id, inject_created=inject_created)

    async def find_one(
            self, query: Union[dict, MotycQuery] = None, *,
            _id=None,
            inject_default_id: bool = None
    ) -> T:
        """ Finds one element in the collection.

        Either query or Mongo's _id should be provided, the second only if collection's identity is default.

        :param query: Raw MongoDB query, advanced query or MotycQuery (see MotycQuery.build_mongo_query)
        :param _id: Mongo's _id of the document to find, will be converted to ObjectId.
        :param inject_default_id: Should _id field be injected into returned model.
        :return: Item found parsed as Model.
        :raises: NotFound if nothing found.
        """

        mongo_query = self.build_mongo_query(query, _id=_id)

        document = await self.collection.find_one(mongo_query)

        if document is None: raise NotFound(mongo_query)
        return self.parse_document(document, inject_default_id=inject_default_id)

    async def update_one(
            self, query: Union[dict, MotycQuery] = None,
            _id=None, *,
            update: Union[dict, MotycQuery],
            inject_default_id=False
    ) -> T:
        """ Updates one element in the collection.

        Either query or Mongo's _id should be provided, the second only if collection's identity is default.

        :param query: Raw MongoDB query, advanced query or MotycQuery (see MotycQuery.build_mongo_query)
        :param update: Raw MongoDB update query, advanced query or MotycQuery (see MotycQuery.build_mongo_query)
        :param _id: Mongo's _id of the document to update, will be converted to ObjectId.
        :param inject_default_id: Should _id field be injected into returned model.
        :return: Updated model instance.
        :raises: NotFound if nothing found.
        """

        mongo_query = self.build_mongo_query(query, _id=_id)
        update_query = self.build_mongo_query(update)

        document = await self.collection.find_one_and_update(
            mongo_query,
            update_query,
            return_document=ReturnDocument.AFTER
        )

        if document is None: raise NotFound(mongo_query)

        return self.parse_document(document, inject_default_id=inject_default_id)

    async def modify(
            self, item: T, update: Union[dict, MotycQuery], *,
            inject_default_id: bool = None,
    ) -> T:
        """ Updates model in the db, based on model instance identity.

        Updates the model, found before with find_one() i.e.
        Call chain of find_one() and then modify() is race-condition safe,
        cause modify() will rise NotFound if the model will be deleted in between.

        :param item: Model instance to modify.
        :param update: Raw MongoDB update query, advanced query or MotycQuery (see MotycQuery.build_mongo_query)
        :param inject_default_id: Should _id field be injected into returned model.
        :return: Updated model instance.
        :raises: NotFound if nothing found.
        """

        assert isinstance(item, BaseModel), "Can only handle BaseModel, not dict i.g."

        document = item.dict(by_alias=True)

        assert document.get(self.identity) is not None, f"Need identity ({self.identity}) to update model."

        return await self.update_one(
            {self.identity: document[self.identity]},
            update,
            inject_default_id=inject_default_id
        )

    async def delete_one(self, query: Union[dict, MotycQuery] = None, *, _id=None):
        """ Deletes one element from the collection.

        Either query or Mongo's _id should be provided, the second only if collection's identity is default.

        :param query: Raw MongoDB query, advanced query or MotycQuery (see MotycQuery.build_mongo_query)
        :param _id: Mongo's _id of the document to delete, will be converted to ObjectId.
        :raises: NotFound if nothing found.
        """
        mongo_query = self.build_mongo_query(query, _id=_id)
        result: DeleteResult = await self.collection.delete_one(mongo_query)
        if result.deleted_count < 1: raise NotFound(mongo_query)

    async def detach(self, item: T) -> T:
        """ Detaches (deletes) model from db, based on model instance identity.

        Deletes the model, found before with find_one() i.e.
        Call chain of find_one() and then detach() is race-condition safe,
        cause modify() will rise NotFound if the model will be deleted in between.

        :param item: Model instance to detach.
        :return: Detached model instance w/o id.
        """

        assert isinstance(item, BaseModel), "Can only handle BaseModel, not dict i.g."
        document = item.dict(by_alias=True)

        assert document.get(self.identity) is not None, f"Need identity ({self.identity}) to detach model."

        await self.delete_one({self.identity: document[self.identity]})

        document[self.identity] = None

        return self.parse_document(document)

    async def find(
            self, query: Union[dict, MotycQuery] = None, *,
            sort: dict = None,
            skip: int = None,
            limit: int = None,
            limit_by: int = None,
            inject_default_id: bool = None,
    ) -> List[T]:
        """ Finds many elements in the collection.
        :param query: Raw MongoDB db query, where MotycFields can be used as keys, or MotycQuery, built with query builder.
        :param sort: Ordered dict where keys are field names or MotycField, values are MongoDB sort options.
        :param skip: Number of documents to skip in db.
        :param limit: Number of documents to limit by db engine.
        :param limit_by: Maximum number of documents to retrieve on None for no limit.
        :param inject_default_id: Should _id field be injected into returned models.
        :return: List of documents, parsed as Models.
        """

        # todo: raw cursor as parameter

        mongo_query = self.build_mongo_query(query) if query else {}

        cursor: AgnosticCursor = self.collection.find(mongo_query)

        if sort is not None:
            cursor = cursor.sort([(k, v) for k, v in self.build_mongo_query(sort).items()])

        if skip is not None:
            cursor = cursor.skip(skip)

        if limit is not None:
            cursor = cursor.limit(limit)

        result = []
        async for document in cursor:
            if limit_by is not None and len(result) >= limit_by: break
            result.append(self.parse_document(document, inject_default_id=inject_default_id))
        return result

    # ----------------------------------------------------
    # Utility API to deal with raw collections

    async def create_indexes(self):
        if self.identity != '_id':
            await self.collection.create_index(self.identity, unique=True)

        if self.indexes: await self.collection.create_indexes([
            i if isinstance(i, IndexModel) else IndexModel(i)
            for i in self.indexes
        ])

    def generate_id(self):
        # todo config in engine
        assert self.identity != '_id', 'Supported only for non default id field'
        return self.id_generator()

    def build_mongo_query(self, query: Union[dict, MotycQuery], *, _id=None):
        if query is not None:
            assert _id is None, "Either query or _id should be provided."
            return MotycQuery.build_mongo_query(query)
        else:
            assert _id is not None, "Either query or _id should be provided."
            assert self.identity == '_id', "_id parameter can be used only if collection's identity is default"
            return {'_id': ObjectId(_id)}

    # ----------------------------------------------------

    # noinspection PyUnusedLocal
    async def _bind(
            self, engine: Engine, db: AgnosticDatabase, t: type, name: str, *,
            inject_motyc_fields=False,
    ):

        models = Collection._check_type_get_basemodels(t)

        self.t = t
        self.db = db
        if self.name is None: self.name = name
        self.collection = getattr(db, self.name)

        if inject_motyc_fields:
            for model in models: MotycField._inject_for_model(model)

    def parse_document(self, document: dict, *, inject_default_id=False, inject_created=False) -> T:
        if self.identity != '_id': assert not inject_default_id, "inject_default_id is not supported with non default identity management."
        model = parse_obj_as(cast(Type[T], self.t), document)
        if inject_default_id: object.__setattr__(model, '_id', document.get('_id', None))
        if inject_created: object.__setattr__(model, '__created__', document.get('__created__', False))
        if hasattr(model, '_bound_collection'): model._bound_collection = self
        return model

    # ----------------------------------------------------

    @staticmethod
    def _check_type_get_basemodels(t: type) -> List[Type[BaseModel]]:
        """ Checks if collection type is subclass of BaseModel or Union of them, returns list of BaseModels involved.
        :param t: Type of collection.
        :return: List of BaseModels, which collection can hold.
        :raise: TypeError if collection type is improper.
        """
        result = []
        if typing_inspect.is_union_type(t):
            for tt in typing_inspect.get_args(t):
                if not issubclass(tt, BaseModel):
                    raise TypeError(f"Args of Union must be BaseModels, {t} not.")
                result.append(tt)
        else:
            try:
                if issubclass(t, BaseModel): result.append(t)
            except TypeError:
                pass

        from pymotyc import MotycModel
        for tt in [*result]:
            for parent in tt.__mro__:
                if parent in [MotycModel, BaseModel]: break
                if parent not in result: result.append(parent)

        if not result: raise TypeError(f"Improper type {t} of the Collection.")

        return result
