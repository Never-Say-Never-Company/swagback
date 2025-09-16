from decouple import config
from pymongo import MongoClient

MONGO_HOST = config("MONGO_HOST", default="localhost")
MONGO_PORT = config("MONGO_PORT", cast=int, default=27017)
MONGO_DB_NAME = config("MONGO_DB_NAME", default="meudb")
MONGO_USER = config("MONGO_USER", default=None)
MONGO_PASSWORD = config("MONGO_PASSWORD", default=None)
MONGO_AUTH_DB = config("MONGO_AUTH_DB", default="admin") 

if MONGO_USER and MONGO_PASSWORD:
    mongo_uri = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}?authSource={MONGO_AUTH_DB}"
else:
    mongo_uri = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB_NAME}"

client = MongoClient(mongo_uri)
db = client[MONGO_DB_NAME]

usuarios = db.usuarios  