from typing import Optional, List, Sequence, Union, Iterable

from motor.motor_asyncio import AsyncIOMotorClient
from typing_extensions import Literal

from pymotyc.util import get_annotations, camel_to_snake


class Engine:
    motor: AsyncIOMotorClient
    databases: List[type]

    def __init__(self):
        self.databases = []

    async def bind(
            self, *,
            motor: AsyncIOMotorClient,
            databases: Iterable = (),
            already_bound: Literal['skip', 'assert'] = 'assert',
            inject_motyc_fields=False,
    ):
        """ Binds Motyc engine and all collected databases/collections with the Motor instance.
        See _bind_database for details.
        :param databases: Databases to bind, alternatively one can use Engine.database decorator.
        :param motor: Motor instance to bind to.
        :param already_bound: What to do, if database already bound.
        :param inject_motyc_fields: Inject MotycFields to all involved Pydantic models,
            to fields be accessible via Model.<field_name> to be used in advanced queries.
        """
        self.motor = motor
        self.databases += databases
        for db in self.databases:

            if already_bound == 'assert':
                assert not hasattr(db, '__pymotyc__bound__'), "Database is already bound."
            elif already_bound == 'skip':
                if hasattr(db, '__pymotyc__bound__'): continue
            else:
                assert False

            setattr(db, '__pymotyc__bound__', self)

            await self._bind_database(db, inject_motyc_fields=inject_motyc_fields)

    def database(self, db):
        self.databases.append(db)
        return db

    # @staticmethod
    # def get_database(db) -> AgnosticDatabase:
    #     assert hasattr(db, '__pymotyc__bound__'), "Database is not managed by PyMotyc."

    @classmethod
    async def create(cls, db_or_dbs: Union[type, Sequence[type]], **kwargs):
        self = cls()
        self.databases += db_or_dbs if isinstance(db_or_dbs, Sequence) else [db_or_dbs]
        await self.bind(**kwargs)
        return self

    async def _bind_database(self, db: type, **kwargs):
        """ Binds database, represented by some class to this engine.
        It runs through attributes and annotations and checks the following:
            - if there is attribute of type Collection there should be annotation Collection[] with type/model inside []
            - if there is annotation like Colletion[] but no attribute, Collection with default settings will be
                created and assigned to attribute
            - if there is Collection annotation without [] error will be rised
            - if there is Collection[] annotation for not a Collection attribute error will be rised
            - all other attributes / annotations will be ignored
        All found collections will be mounted to engine and can be used then to query things.
        :param db: db class
        :param kwargs: kwargs to pass to Collection._bind
        :raise: AssertionError if errors in db definition syntax
        """
        from pymotyc.collection import Collection

        def check_annotation(annotation) -> Optional[type]:
            """ Checks if annotation of database class member is correct Collection annotation.
            :param annotation: annotation
            :return: type or None
                - type if annotation is correct Collection[] annotation
                - None otherwise
            :raise: AssertionError if annotation is Collection without []
            """
            # first check is annotation is GenericAlias
            # https://stackoverflow.com/questions/49171189/whats-the-correct-way-to-check-if-an-object-is-a-typing-generic

            if issubclass(getattr(annotation, '__origin__', None), Collection):
                return annotation.__args__[0]

            # then check annotation is not Collection without []
            if isinstance(annotation, type):  # like Collection without []
                assert not issubclass(annotation, Collection), "Always use Collection with [] in annotations."

            # we don't care all other cases
            return None

        annotations = get_annotations(db)
        attributes = dir(db)
        for attr_name in {*annotations, *attributes}:
            t = check_annotation(annotations[attr_name]) if attr_name in annotations else None
            if attr_name in attributes:
                attr = getattr(db, attr_name)
                if not isinstance(attr, Collection):
                    # ignore, but check annotation is not Collection first
                    assert t is None, f"Do not use Collection[] annotation for non Collection() attribute {attr_name}."
                    continue

                assert t is not None, f"There should be annotation Collection[] for attribute '{attr_name}' of type Collection."
            else:
                # ignore non Collection annotations
                if t is None: continue
                # Create collection with default settings
                setattr(db, attr_name, Collection())

            collection: Collection = getattr(db, attr_name)

            db_name = getattr(db, '__db__name__', None)
            if db_name is None: db_name = camel_to_snake(db.__name__)

            await collection._bind(self, getattr(self.motor, db_name), t, attr_name, **kwargs)
