from pymongo.errors import PyMongoError


class MotycError(Exception):
    pass


class NotFound(MotycError):
    def __init__(self, query: dict):
        super().__init__(f"No item found for query {query}.")
        self.query = query


# class Exists(MotycError):  # is it really needed?
#     def __init__(self, original_exception: PyMongoError):
#         self.original_exception = original_exception
