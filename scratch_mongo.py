import asyncio

from bson import ObjectId
from motor.core import AgnosticDatabase, AgnosticCollection
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    db: AgnosticDatabase = motor.db
    collection: AgnosticCollection = db.collection

    await collection.drop()
    await collection.create_index('foo', unique=True)
    result: InsertOneResult = await collection.insert_one({'foo': 1})

    result: UpdateResult = await collection.update_one({'foo': 1}, {'$push': {'bar': 1}})

    print(await collection.find_one({'foo': 1}))

    # result = await collection.find_one({'foo': 1})
    #
    # _id = str(result['_id'])
    # result = await collection.find_one({'_id': _id})
    # print(result)




    # try:
    #     result: InsertOneResult = await collection.insert_one({'foo': 1})
    # except DuplicateKeyError as e:
    #     for k in dir(e): print(k, e.__dict__.get(k))

    # result: UpdateResult = await collection.update_one(
    #     {'foo': 2},
    #     {'$set': {'foo': 2, 'bar': 2}}
    # )
    #
    # print(result.raw_result)


    # result: InsertOneResult = await collection.insert_one({'foo': 1})
    # result: InsertOneResult = await collection.insert_one({'foo': 2})
    # result: InsertOneResult = await collection.insert_one({'foo': 2})

    # document = await collection.find_one_and_update(
    #     {'foo': 4},
    #     {'$set': {'x': 1}},
    #     return_document=ReturnDocument.AFTER
    # )

    # print(document)

    # result: DeleteResult = await collection.delete_one({'foo': 0})
    # print(result.deleted_count)

    # result: UpdateResult = await collection.update_one({'foo': 2}, {'$inc': {'foo': 4}})


asyncio.run(main())

# async def old():
#     result: InsertOneResult = await some.insert_one({'foo': 2})
#
#     # print('#1')
#     # print(result.inserted_id, type(result.inserted_id))
#
#     _id = result.inserted_id
#     result: UpdateResult = await some.update_one({'_id': _id}, update={'$set': {'foo': 5}}, upsert=True)
#
#     _id = ObjectId()
#     result: UpdateResult = await some.update_one({'_id': _id}, update={'$set': {'foo': 15}}, upsert=True)
#
#     print(await some.find().sort('foo', 1).to_list(100))
#
#     # result: UpdateResult = await some.update_one({'foo': 1}, update={'$set': {'foo': 5}}, upsert=True)
#     # print('#2')
#     # print(result.raw_result)
#     # print(result.upserted_id)
#     #
#     # result: UpdateResult = await some.update_one({'foo': 2}, update={'$set': {'foo': 2}}, upsert=True)
#     # print(result.raw_result)
#     # print(result.upserted_id)
