import asyncio

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

# import like this
from pymotyc import MotycModel, Engine, Collection, M

# ====================================================

engine = Engine()


# ====================================================


# @engine.inject_motycfields todo плохо - модели то в другом месте, надо сделать нормальный парсинг
class Address(BaseModel):
    index: int
    street: str


class Supplier(BaseModel):
    address: Address


# ====================================================


@engine.database
class Warehouse:
    suppliers: Collection[Supplier]


async def main():
    motor = AsyncIOMotorClient("mongodb://127.0.0.1:27017")
    await engine.bind(motor=motor, inject_motyc_fields=True)
    await Warehouse.suppliers.collection.drop()

    m = await Warehouse.suppliers.save(Supplier(address=Address(index=127540, street="Dubninskaya")), inject_default_id=True)



    # print(await Warehouse.suppliers.find({'address.index': 127540}))
    # print(await Warehouse.suppliers.find({'address': {'index': 127540, 'street': "Dubninskaya"}}))
    # print(await Warehouse.suppliers.find({'address': {'index': 127540, 'street': "Dubninskaya"}}))
    # print(await Warehouse.suppliers.find({Supplier.address: {'index': 127540, 'street': "Dubninskaya"}}))
    # print(await Warehouse.suppliers.find((M(Supplier.address.index) == 127540) & (M(Supplier.address.street) == "Dubninskaya")))  # todo
    # # print(await Warehouse.suppliers.find({Supplier.address: {Address.index: 127540, Address.street: "Dubninskaya"}})) todo
    # print(await Warehouse.suppliers.find({Supplier.address: Address(index=127540, street="Dubninskaya")}))
    #
    # print("Everything fine!")


if __name__ == "__main__":
    asyncio.run(main())
