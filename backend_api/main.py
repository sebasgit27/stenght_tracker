from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import SQLModel, Session

# Importas tus módulos locales
from database import engine, get_session
import models # Importante: Al importar el archivo entero, SQLModel registra todas las clases en su memoria

from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import select
from fastapi import HTTPException

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Genera los CREATE TABLE en PostgreSQL basándose en las clases de models.py
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan, title="Strength Tracker API")

# Endpoint para guardar la serie
@app.post("/api/sets/")
def create_workout_set(workout_set: models.WorkoutSet, db: Session = Depends(get_session)):
    db.add(workout_set)
    db.commit()
    db.refresh(workout_set)
    return workout_set

# 1. Endpoint para crear tu usuario
@app.post("/api/users/")
def create_user(user: models.User, db: Session = Depends(get_session)):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# 2. Endpoint para registrar ejercicios en el catálogo
@app.post("/api/exercises/")
def create_exercise(exercise: models.Exercise, db: Session = Depends(get_session)):
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise

# 3. El DTO: Esquema exclusivo para validar el JSON que recibimos
class RoutineCreate(BaseModel):
    name: str
    user_id: int
    exercise_ids: List[int]

# 3.2. El Endpoint para crear la rutina y enlazar los ejercicios
@app.post("/api/routines/")
def create_routine(routine_data: RoutineCreate, db: Session = Depends(get_session)):
    """
    Crea una nueva rutina y la vincula con los ejercicios existentes en la BD.
    """
    # a. Crear el objeto Rutina base (en memoria)
    new_routine = models.Routine(name=routine_data.name, user_id=routine_data.user_id)
    
    # b. Buscar los ejercicios en la base de datos que coincidan con los IDs pasados
    # Usamos la sintaxis de select() de SQLModel para traerlos de golpe
    statement = select(models.Exercise).where(models.Exercise.id.in_(routine_data.exercise_ids))
    exercises_found = db.exec(statement).all()
    
    # c. ¡La magia del ORM! Asignamos la lista de objetos a la propiedad de la clase.
    # SQLModel entenderá esto y escribirá automáticamente en la tabla RoutineExerciseLink
    new_routine.exercises = exercises_found
    
    # d. Persistir en disco
    db.add(new_routine)
    db.commit()
    db.refresh(new_routine)
    
    return new_routine

from datetime import datetime, timezone

@app.post("/api/sessions/")
def create_session(session: models.Session, db: Session = Depends(get_session)):
    """
    Inicia una nueva sesión de entrenamiento para un usuario.
    Puede estar vinculada a una rutina predefinida o ser un entreno libre.
    """
    # Si tu modelo no pone la fecha automáticamente, podemos asegurarnos aquí
    if not session.date:
        session.date = datetime.now(timezone.utc)
        
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@app.get("/api/users/{user_id}/routines/")
def get_user_routines(user_id: int, db: Session = Depends(get_session)):
    """
    Devuelve la lista de rutinas disponibles para un usuario concreto.
    """
    # Buscamos al usuario primero para asegurarnos de que existe
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Si existe, la magia de las 'Relationships' de SQLModel hace el resto
    return user.routines


@app.get("/api/routines/{routine_id}/exercises/")
def get_routine_exercises(routine_id: int, db: Session = Depends(get_session)):
    """
    Devuelve los ejercicios que pertenecen a una rutina específica.
    """
    routine = db.get(models.Routine, routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    
    return routine.exercises


@app.get("/api/users/{user_id}/exercises/{exercise_id}/history/")
def get_exercise_history(user_id: int, exercise_id: int, db: Session = Depends(get_session)):
    """
    Devuelve todas las series históricas de un usuario para un ejercicio concreto.
    """
    # Hacemos un JOIN cruzando las series con las sesiones para filtrar por usuario
    statement = (
        select(models.WorkoutSet)
        .join(models.Session)
        .where(models.Session.user_id == user_id)
        .where(models.WorkoutSet.exercise_id == exercise_id)
        .order_by(models.Session.date.desc()) # Ordenamos de más reciente a más antiguo
    )
    
    history = db.exec(statement).all()
    return history


@app.delete("/api/sets/{set_id}")
def delete_workout_set(set_id: int, db: Session = Depends(get_session)):
    """Elimina una serie concreta del historial."""
    # 1. Buscamos la serie
    set_to_delete = db.get(models.WorkoutSet, set_id)
    
    # 2. Si no existe, devolvemos un error 404
    if not set_to_delete:
        raise HTTPException(status_code=404, detail="Serie no encontrada")
    
    # 3. La borramos de la memoria y hacemos el commit a la base de datos
    db.delete(set_to_delete)
    db.commit()
    
    return {"message": "Serie eliminada correctamente"}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_session)):
    """Elimina un entrenamiento completo."""
    session_to_delete = db.get(models.Session, session_id)
    
    if not session_to_delete:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    db.delete(session_to_delete)
    db.commit()
    
    return {"message": "Sesión eliminada correctamente"}

class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    exercise_ids: List[int]
    
@app.put("/api/routines/{routine_id}")
def update_routine(routine_id: int, routine_data: RoutineUpdate, db: Session = Depends(get_session)):
    """
    Actualiza el nombre de una rutina y REEMPLAZA su lista de ejercicios.
    """
    # 1. Buscamos la rutina
    routine = db.get(models.Routine, routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    
    # 2. Actualizamos el nombre si nos has enviado uno nuevo
    if routine_data.name:
        routine.name = routine_data.name
        
    # 3. Buscamos los nuevos ejercicios en la base de datos
    statement = select(models.Exercise).where(models.Exercise.id.in_(routine_data.exercise_ids))
    new_exercises = db.exec(statement).all()
    
    # 4. ¡La magia! Reemplazamos la lista. 
    # SQLAlchemy automáticamente borrará los enlaces viejos y creará los nuevos
    # en la tabla RoutineExerciseLink.
    routine.exercises = new_exercises
    
    # 5. Guardamos los cambios
    db.add(routine)
    db.commit()
    db.refresh(routine)
    
    return routine