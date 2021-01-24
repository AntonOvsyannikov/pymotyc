import pytest

from tests.integration import db


async def test_simple_query():
    await db.Warehouse.empolyees.collection.drop()
    await db.Warehouse.empolyees.save(db.vasya)
    await db.Warehouse.empolyees.save(db.frosya)

    assert await db.Warehouse.empolyees.find(sort={'age': 1}) == [db.frosya, db.vasya]

    await db.Warehouse.products.collection.drop()

    book = await db.Warehouse.products.save(db.book)
    assert isinstance(book.id, str)
    assert book.id is not None
    book_id = book.id

    book.pages = 43
    await db.Warehouse.products.save(book)

    computer = await db.Warehouse.products.save(db.computer)
    computer_id = computer.id

    assert await db.Warehouse.products.collection.count_documents({}) == 2

    computer = await db.Warehouse.products.find_one({'id': computer_id})
    assert isinstance(computer, db.Computer)
    assert computer.vendor == 'Apple'

    book = await db.Warehouse.products.find_one({'id': book_id})
    assert isinstance(book, db.Book)
    assert book.pages == 43
