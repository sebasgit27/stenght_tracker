from sqlmodel import create_engine, Session

# Reemplaza con tus credenciales reales (idealmente usando variables de entorno)
# Formato: postgresql://usuario:contraseña@host:puerto/nombre_bd
DATABASE_URL = "postgresql://postgres:tu_password@localhost:5432/strength_tracker"

# El engine es la conexión física a la BD
engine = create_engine(DATABASE_URL, echo=True) # echo=True imprime el SQL en la terminal (genial para debuggear)

def get_session():
    """Generador de sesiones para la base de datos"""
    with Session(engine) as session:
        yield session