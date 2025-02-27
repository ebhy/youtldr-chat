"""Main entrypoint for the app."""
import logging
import pickle
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from langchain.vectorstores import VectorStore

from callback import QuestionGenCallbackHandler, StreamingLLMCallbackHandler
from query_data import get_chain
from schemas import ChatResponse, ChatInput
from loader import RawLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.embeddings.openai import OpenAIEmbeddings
from utils import increment_column_today

app = FastAPI()
templates = Jinja2Templates(directory="templates")
vectorstore: Optional[VectorStore] = None


@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/chat")
async def websocket_endpoint(
    *,
    websocket: WebSocket,
):    
    await websocket.accept()
    question_handler = QuestionGenCallbackHandler(websocket)
    stream_handler = StreamingLLMCallbackHandler(websocket)
    chat_history = []
    
    
    # Generate vectorstore
    logging.info("Building Vectorstore...")
    # First message is websocket
    text = await websocket.receive_text()
    resp = ChatResponse(sender="bot", message="", type="init")
    await websocket.send_json(resp.dict())

    # At this point do analytics
    try:
        increment_column_today()
    except:
        pass

    logging.info(f"Text recieved: {text}")
    loader = RawLoader(text=text)
    
    # The below is just what happens inside VectorstoreIndexCreator
    # from langchain.text_splitter import RecursiveCharacterTextSplitter
    # text_splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=1000,
    #     chunk_overlap=200,
    # )
    # documents = text_splitter.split_documents(raw_documents)
    # from langchain.embeddings import OpenAIEmbeddings
    # embeddings = OpenAIEmbeddings()
    # vectorstore = FAISS.from_documents(documents, embeddings)

    index = VectorstoreIndexCreator(
        embedding=OpenAIEmbeddings(model="gpt-3.5-turbo")).from_loaders([loader])
    logging.info("Vectorstore built!")
    vectorstore = index.vectorstore

    qa_chain = get_chain(vectorstore, question_handler, stream_handler)
    # Use the below line instead of the above line to enable tracing
    # Ensure `langchain-server` is running
    # qa_chain = get_chain(vectorstore, question_handler, stream_handler, tracing=True)

    # qa_chain = ConversationalRetrievalChain.from_llm(
    #     llm = ChatOpenAI(temperature=0.0, model_name='gpt-3.5-turbo'),
    #     retriever=vectorstore.as_retriever()
    # )

    while True:
        try:
            # Receive and send back the client message
            question = await websocket.receive_text()
            resp = ChatResponse(sender="you", message=question, type="stream")
            await websocket.send_json(resp.dict())

            # Construct a response
            start_resp = ChatResponse(sender="bot", message="", type="start")
            await websocket.send_json(start_resp.dict())

            result = await qa_chain.acall(
                {"question": question, "chat_history": chat_history}
            )
            chat_history.append((question, result["answer"]))

            end_resp = ChatResponse(sender="bot", message="", type="end")
            await websocket.send_json(end_resp.dict())
        except WebSocketDisconnect:
            logging.info("websocket disconnect")
            break
        except Exception as e:
            logging.error(e)
            resp = ChatResponse(
                sender="bot",
                message=f"Sorry, something went wrong ({str(e)}) Try again.",
                type="error",
            )
            await websocket.send_json(resp.dict())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
