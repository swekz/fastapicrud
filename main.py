from bson import ObjectId
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional
from hashlib import sha256

import uvicorn

# Initialize FastAPI app
app = FastAPI()

# Database configuration
client = MongoClient("mongodb://localhost:27017/")   #--database connection
db = client["remotebricks"]          #--database name
users_collection = db["users"]        #--collection name
anothers_collection = db["details"]   #--collection name

# Utility function to hash passwords
def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

# Data models
#-----for registration----
class UserRegistration(BaseModel):
    username : str
    email: str
    password: str

#--------for login-------
class UserLogin(BaseModel):
    email: str
    password: str

#--------for linking id------
class LinkID(BaseModel):
    user_id: str
    linked_id: str

#-------to add details in multiple collection--
class Details(BaseModel):
    age: int
    user_id: str
    location: str

#-----------delete user
class Deletedata(BaseModel):
    user_id: str

def serialize_object_id(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError("Type not serializable")

# API Endpoints
#--------registration of users---------------
@app.post("/register")
async def register(user: UserRegistration):
    # Check if user already exists
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if users_collection.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the password and store user details
    hashed_password = hash_password(user.password)
    users_collection.insert_one({
        "username": user.username,
        "email": user.email,
        "password": hashed_password
    })
    return {"message": "User registered successfully"}

#------------------Login endpoint--------------------
@app.post("/login")
async def login(user: UserLogin):
    # Verify user credentials
    user_data = users_collection.find_one({"email": user.email})
    if not user_data:
        return {"message": "signup before login"}
    if not user_data or user_data["password"] != hash_password(user.password):
        return {"message":"Password mismatch"}
    return {"message": "Login successful"}

#-------------------link id endpoint------------------
@app.post("/link-id")
async def link_id(link_id: LinkID):
    # Convert string user_id to ObjectId
    try:
        user_id = ObjectId(link_id.user_id)
        # Find the user by ObjectId
        user = users_collection.find_one({"_id": user_id})

        if not user:
            return {"message": "User ID not found"}
        
        # Link ID to user's account
        result = users_collection.update_one(
            {"_id": user_id},  # Use the correct ObjectId here
            {"$set": {"linked_id": link_id.linked_id}}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "ID linked successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

#-----------------add details of users with _id and save in different collection------------
@app.post("/add_details")
async def details(data : Details):
    try:
        user_id = ObjectId(data.user_id)
        # Find the user by ObjectId
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return {"message": "User ID not found"}

        ad = anothers_collection.find_one({"_id": user_id})

        if ad:
            return {"message":"User ID already exists"}
        
        anothers_collection.insert_one({
            "_id":user_id,
            "age": data.age,
            "location": data.location
        })
        return {"message": "Details updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

#---------------------delete users and their data from all collections----
@app.delete("/delete_user")
async def delete_user(user_id: Deletedata):
    try:
        # Convert user_id to ObjectId
        user_id_object = ObjectId(user_id.user_id)

        # Check if user exists
        user = users_collection.find_one({"_id": user_id_object})
        if not user:
            return {"message":"User not found in users collection"}
        
        # Check if user exists
        user1 = anothers_collection.find_one({"_id": user_id_object})
        if not user1:
            return {"message":"User not found in details collection"}
        
        # Delete associated details
        details_result = anothers_collection.delete_many({"_id": user_id_object})

        # Delete the user
        user_result = users_collection.delete_one({"_id": user_id_object})

        # Check if user was deleted
        if user_result.deleted_count == 0:
            return {"message":"User not found"}

        # Return success message
        return {
            "message": "User and associated data deleted successfully",
            # "orders_deleted": orders_result.deleted_count,
            # "details_deleted": details_result.deleted_count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")

#-----------join data of multiple collections --------------------------------
@app.get("/join")
async def get_user_orders():

    try:
        data = list(users_collection.aggregate([
            {"$lookup": {
                "from": "anothers_collection",
                "localField": "linked_ids",
                "foreignField": "_id",
                "as": "joined_data"
            }}
        ]))
        return [dict(item, **{'_id': serialize_object_id(item['_id'])}) for item in data]
    except Exception as e:
        # logging.error(f"Error in join_collections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1",port=4000, reload=True)

