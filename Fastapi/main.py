from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from uvicorn import run
import sqlite
import translate 

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression middleware
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  
)


app.mount("/sqlite",sqlite.app)
app.mount("/translate",translate.app)


@app.get('/api_checker')
async def api_checker():

    field_info="API Test Successful"
    return JSONResponse(content=field_info)


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8001)




