from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

# 1. TABLA INTERMEDIA (Many-to-Many)
class RoutineExerciseLink(SQLModel, table=True):
    # Usamos PK compuesta para evitar duplicados exactos en la BD
    routine_id: Optional[int] = Field(default=None, foreign_key="routine.id", primary_key=True)
    exercise_id: Optional[int] = Field(default=None, foreign_key="exercise.id", primary_key=True)

# 2. TABLA USUARIOS
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # Relaciones (One-to-Many)
    routines: List["Routine"] = Relationship(back_populates="user")
    exercises: List["Exercise"] = Relationship(back_populates="user")
    sessions: List["Session"] = Relationship(back_populates="user")

# 3. TABLA EJERCICIOS
class Exercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    # Conexiones bidireccionales
    user: Optional[User] = Relationship(back_populates="exercises")
    # AQUI ESTA LA MAGIA DEL N:M
    routines: List["Routine"] = Relationship(back_populates="exercises", link_model=RoutineExerciseLink)

# 4. TABLA RUTINAS
class Routine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    user: Optional[User] = Relationship(back_populates="routines")
    sessions: List["Session"] = Relationship(back_populates="routine")
    # Conexión N:M con los ejercicios
    exercises: List[Exercise] = Relationship(back_populates="routines", link_model=RoutineExerciseLink)

# 5. TABLA SESIONES
class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Forma moderna y segura de obtener el timestamp UTC
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    routine_id: Optional[int] = Field(default=None, foreign_key="routine.id")
    
    user: Optional[User] = Relationship(back_populates="sessions")
    routine: Optional[Routine] = Relationship(back_populates="sessions")

    workout_sets: List["WorkoutSet"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

# 6. TABLA SERIES (Renombrado a WorkoutSet)
class WorkoutSet(SQLModel, table=True):
    __tablename__ = "workout_set" # Fuerzas el nombre de la tabla en PostgreSQL
    
    id: Optional[int] = Field(default=None, primary_key=True)
    num_set: int
    reps: int
    weight: Optional[float] = None
    added_weight: Optional[float] = None
    rir: int
    time_rest: Optional[int] = None
    notes: Optional[str] = None
    
    session_id: Optional[int] = Field(default=None, foreign_key="session.id")
    exercise_id: Optional[int] = Field(default=None, foreign_key="exercise.id")
    
    session: Optional[Session] = Relationship(back_populates="workout_sets")
    # También deberías enlazar el set con el ejercicio para saber qué estabas levantando
    exercise: Optional[Exercise] = Relationship()


