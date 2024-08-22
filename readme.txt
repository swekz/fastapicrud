#-----install packages
step 1 : pip install -r requirements.txt

#--------to run application------------
step 2: uvicorn main:app --reload --port 4000

#------------import api collection--------------
step 3 : import postman api collections from remotebrickspostman_collection.json