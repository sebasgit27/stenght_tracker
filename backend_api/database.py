import os
from dotenv import load_dotenv
from sqlmodel import create_engine, Session

# Esto lee tu archivo .env y carga las variables en el entorno
load_dotenv() 

# Obtenemos la URL exacta que pusiste en el .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Creamos el motor. echo=True imprimirá las consultas SQL en la terminal
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    """Generador de sesiones para inyectar en los endpoints de FastAPI"""
    with Session(engine) as session:
        yield session