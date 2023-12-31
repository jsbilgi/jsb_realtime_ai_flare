# from typing import List

from fastapi import FastAPI, Depends
from pydantic import BaseModel

from utils.localCORS import permitReactLocalhostClient
from db import get_astra
from ai import get_embeddings, get_vectorstore, load_pdf_from_url, get_chat_model, get_flare_chain
from users import get_user_store, files_for_user, add_file_to_user

db, keyspace = get_astra()
embeddings = get_embeddings()
vectorstore = get_vectorstore(embeddings, db, keyspace)
chatmodel = get_chat_model()
flarechain = get_flare_chain(chatmodel, vectorstore)
user_store = get_user_store(db, keyspace)

class ListFileRequest(BaseModel):
    user_id: str

class LoadPDFRequest(BaseModel):
    user_id: str
    file_url: str

class QuestionRequest(BaseModel):
    user_id: str
    question_id: str
    question: str

# app

app = FastAPI()
permitReactLocalhostClient(app)


@app.get('/')
def index():
    return {
        'db': str(db),
        'keyspace': str(keyspace),
        'embeddings': str(embeddings),
        'vectorstore': str(vectorstore),
    }


@app.post('/list_files')
def list_files(payload: ListFileRequest):
    return files_for_user(user_store, payload.user_id)


@app.post('/load_pdf_url')
def load_pdf_url(payload: LoadPDFRequest):
    try:
        n_rows, file_name = load_pdf_from_url(payload.file_url, vectorstore)
        if n_rows is not None:
            add_file_to_user(user_store, payload.user_id, file_name)
            return {
                "success": True,
                "n_rows": n_rows,
            }
        else:
            return {
                "success": False,
            }
    except Exception:
        return {
            "success": False,
        }


@app.post('/flare_ask')
def flare_ask(payload: QuestionRequest):
    import time
    if payload.question[0].upper() == 'Z':
        # a fake failure
        time.sleep(0.5)
        return {
            "question_id": payload.question_id,
            "success": False,
        }
    else:
        result = flarechain.run(payload.question)
        #
        return {
            "question_id": payload.question_id,
            "success": True,
            "answer": result,
        }
