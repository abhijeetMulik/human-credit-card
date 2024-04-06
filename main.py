import os
import uuid
import pickle
import datetime
import time
import shutil
import bcrypt

import cv2
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
from fastapi.middleware.cors import CORSMiddleware
import face_recognition
import starlette
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session

TRANSACTION_LOG_DIR = './logs'
DB_PATH = './db'
for dir_ in [TRANSACTION_LOG_DIR, DB_PATH]:
    if not os.path.exists(dir_):
        os.mkdir(dir_)

app = FastAPI()
models.Base.metadata.create_all(bind=engine)  # create all tables in postgresql

class User(BaseModel):
    email: str
    password: str
    picture_embeddings: str
    security_pin: int

class Transaction(BaseModel):
    transaction_date: datetime.date
    total_payment: float

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login(db: db_dependency, file: UploadFile = File(...)):

    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()

    #save the file
    with open(file.filename, "wb") as f:
        f.write(contents)

    user_name, match_status = recognize(cv2.imread(file.filename))

    if match_status:
        epoch_time = time.time()
        date = time.strftime('%Y%m%d', time.localtime(epoch_time))
        with open(os.path.join(TRANSACTION_LOG_DIR, '{}.csv'.format(date)), 'a') as f:
            f.write('{},{},{}\n'.format(user_name, datetime.datetime.now(), 'IN'))
            f.close()

    result = db.query(models.Users).filter(models.Users.picture_embeddings == user_name).first()
    if not result:
        raise HTTPException(status_code=404, detail='User not found')

    return {'user': result.name, 'filename': user_name}
    # return {'user': result, 'match_status': match_status}

@app.post("/register_new_user")
async def register_new_user(db: db_dependency ,file: UploadFile = File(...), text=None, security_pin=None, email=None):  # security_pin, card number, cvv pin

    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()

    # save the file
    with open(file.filename, "wb") as f:
        f.write(contents)

    embeddings = face_recognition.face_encodings(cv2.imread(file.filename))

    unique_filename = uuid.uuid4()  # Generate a UUID (Universally Unique Identifier)

    db_insert = models.Users(email=email, name= text, picture_embeddings= unique_filename, security_pin= security_pin, password= 'password')
    db.add(db_insert)
    db.commit()

    unique_filename = f"{unique_filename}.pickle"

    file_ = open(os.path.join(DB_PATH, unique_filename), 'wb')
    pickle.dump(embeddings, file_)
    os.remove(file.filename)

    return {'registration_status': 200}

@app.post("/insert_transaction")
async def insert_transaction(db: db_dependency ,user_email, transaction_date, total_payment= 0.0):
    db_insert = models.Transactions(user_email=user_email, transaction_date= transaction_date, total_payment= total_payment)
    db.add(db_insert)
    db.commit()
    return {'transaction inserted successfully': 200}

@app.post("/profile_login")
async def profile_login(db: db_dependency, user_email=None, password=None):
    if not user_email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    user = db.query(models.Users).filter(models.Users.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Check if the entered password matches the stored hashed password
    if bcrypt.checkpw(password.encode('utf-8'), user.password):
        return {"message": "Login successful!"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect password.")

@app.post("/profile_registration")
async def profile_registration(db: db_dependency, user_email=None, password=None):
    if user_email is None or password is None:
        raise HTTPException(status_code=401, detail="Invalid user credentials")
    user_exists = db.query(models.Users).filter(models.Users.email == user_email).first()
    if user_exists:
        raise HTTPException(status_code=404, detail='User already exists.')
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db_insert = models.Users(email=user_email, password=hashed_password)
    db.add(db_insert)
    db.commit()
    return {"message": "Registration successful"}

@app.get("/get_transaction_history")
async def transaction_history(db: db_dependency ,user_emai):
    result = db.query(models.Transactions).filter(models.Transactions.user_email == user_emai).all()
    if not result:
        raise HTTPException(status_code=404, detail='Zero transactions found')
    return result

@app.get("/get_transaction_logs")
async def get_attendance_logs():

    filename = 'out.zip'

    shutil.make_archive(filename[:-4], 'zip', TRANSACTION_LOG_DIR)

    ##return File(filename, filename=filename, content_type="application/zip", as_attachment=True)
    return starlette.responses.FileResponse(filename, media_type='application/zip',filename=filename)

def recognize(img):
    # it is assumed there will be at most 1 match in the db

    embeddings_unknown = face_recognition.face_encodings(img)
    # print('user embeddings ********* ==  ',embeddings_unknown)
    if len(embeddings_unknown) == 0:
        return 'no_persons_found', False
    else:
        embeddings_unknown = embeddings_unknown[0]

    match = False
    j = 0

    db_dir = sorted([j for j in os.listdir(DB_PATH) if j.endswith('.pickle')])
    # db_dir = sorted(os.listdir(DB_PATH))    
    print(db_dir)
    while ((not match) and (j < len(db_dir))):

        path_ = os.path.join(DB_PATH, db_dir[j])

        file = open(path_, 'rb')
        embeddings = pickle.load(file)[0]

        match = face_recognition.compare_faces([embeddings], embeddings_unknown)[0]

        j += 1

    if match:
        return db_dir[j - 1][:-7], True
    else:
        return 'unknown_person', False