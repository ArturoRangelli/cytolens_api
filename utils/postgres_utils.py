"""
Copyright (c) 2025 Binary Core LLC. All rights reserved.

This file is part of CytoLens, a proprietary product of Binary Core LLC.
Unauthorized copying, modification, or distribution of this file,
via any medium, is strictly prohibited.

PostgreSQL database utilities and models
"""

from contextlib import contextmanager

from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker

from core import config, constants
from utils import sys_utils

# Database connection
db_uri = config.settings.database_url
engine = create_engine(
    url=db_uri,
    pool_pre_ping=True,  # Check connection health before using
    pool_recycle=3600,  # Recycle connections after an hour
)
Base = declarative_base()
session_factory = sessionmaker(bind=engine)
session = scoped_session(session_factory)


# Models


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")

    slides = relationship("Slide", back_populates="owner")
    tasks = relationship("InferenceTask", back_populates="user")


class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    created_at = Column(String, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)

    original_filename = Column(String, nullable=False)
    type = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)

    # Enforce unique slide name per user at the DB level
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_slide_name_per_user"),
    )

    # Relationships
    owner = relationship("User", back_populates="slides")
    model = relationship("Model", back_populates="slide")
    report = relationship(
        "Report", uselist=False, back_populates="slide", cascade="all, delete-orphan"
    )
    tasks = relationship(
        "InferenceTask", back_populates="slide", cascade="all, delete-orphan"
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)  # user-defined label
    created_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=True)  # nullable = never expires

    # Relationships
    user = relationship("User")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slide_id = Column(Integer, ForeignKey("slides.id"), nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(String, nullable=False)

    slide = relationship("Slide", back_populates="report")


class Model(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    slide = relationship("Slide", back_populates="model")


class InferenceTask(Base):
    __tablename__ = "inference_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inference_task_id = Column(
        String, unique=True, nullable=False
    )  # External task ID from inference service
    slide_id = Column(Integer, ForeignKey("slides.id"), nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # Who requested it

    # Task status and config
    state = Column(
        String, nullable=False, default=constants.TaskState.PENDING
    )  # Celery states: PENDING, STARTED, SUCCESS, FAILURE, REVOKED
    confidence = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)

    # Results and errors
    message = Column(Text, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_task_slide_user", "slide_id", "user_id"),
        Index("idx_task_state", "state"),
    )

    # Relationships
    slide = relationship("Slide", back_populates="tasks")
    user = relationship("User", back_populates="tasks")


# Initialize database tables
Base.metadata.create_all(engine)


# Context manager for session handling
@contextmanager
def session_scope():
    """
    Provide a transactional scope for database operations.
    Ensures the session is properly cleaned up after use.
    """
    try:
        yield session  # Provide the session to the caller
        session.commit()
    except Exception:
        session.rollback()  # Roll back the transaction on error
        raise
    finally:
        session.remove()  # Clean up session resources


# Utility function
def model_to_dict(obj):
    """
    Convert a SQLAlchemy model instance into a dictionary,
    excluding SQLAlchemy internal attributes.
    """
    return {
        key: value
        for key, value in vars(obj).items()
        if not key.startswith("_sa_instance_state")
    }


# User operations
def set_user(username: str, password_hash: str, role: str = "user") -> dict:
    """
    Create a new user in the database.
    """
    with session_scope() as s:
        user = User(username=username, password_hash=password_hash, role=role)
        s.add(user)
        s.flush()
        return model_to_dict(user)


def get_user_by_username(username: str) -> dict | None:
    """
    Retrieve a user object by username.
    """
    with session_scope() as s:
        user = s.query(User).filter_by(username=username).first()
        if user:
            return model_to_dict(user)
        return None


def get_user_by_apikey(hashed_key: str) -> dict | None:
    """
    Return the user associated with the given hashed API key.
    """
    with session_scope() as s:
        api_key = s.query(ApiKey).filter_by(key=hashed_key).first()
        if api_key and api_key.user:
            return model_to_dict(api_key.user)
        return None


# ApiKey operations
def set_apikey(
    user_id: int, hashed_key: str, name: str, expires_at: str = None
) -> dict:
    """
    Create a new API key for a user.
    """
    with session_scope() as s:
        created_at = sys_utils.get_utc_timestamp()
        api_key = ApiKey(
            user_id=user_id,
            key=hashed_key,
            name=name,
            created_at=created_at,
            expires_at=expires_at,
        )

        s.add(api_key)
        s.flush()
        return model_to_dict(api_key)


def get_apikey_by_name(user_id: int, name: str) -> dict | None:
    """
    Get an API key by name for a specific user.
    """
    with session_scope() as s:
        api_key = s.query(ApiKey).filter_by(user_id=user_id, name=name).first()
        if api_key:
            return model_to_dict(api_key)
        return None


# Slide operations
def set_slide(
    name: str,
    model_id: int,
    owner_id: int,
    created_at: str,
    original_filename: str,
    type: str,
    file_size: int,
) -> dict:
    """
    Insert a new slide into the database.
    """
    with session_scope() as s:
        slide = Slide(
            name=name,
            model_id=model_id,
            owner_id=owner_id,
            created_at=created_at,
            original_filename=original_filename,
            type=type,
            file_size=file_size,
        )
        s.add(slide)
        s.flush()  # So slide.id is available before commit
        return model_to_dict(slide)


def update_slide(slide_id: int, owner_id: int, **fields_to_update) -> dict | None:
    """
    Update specific fields of a slide by slide_id and owner_id.
    """
    with session_scope() as s:
        slide = s.query(Slide).filter_by(id=slide_id, owner_id=owner_id).first()
        if not slide:
            return None

        for key, value in fields_to_update.items():
            if hasattr(slide, key):
                setattr(slide, key, value)

        s.flush()
        return model_to_dict(slide)


def delete_slide(slide_id: int, owner_id: int) -> None:
    """
    Delete a slide by slide_id and owner_id.
    """
    with session_scope() as s:
        slide = s.query(Slide).filter_by(id=slide_id, owner_id=owner_id).first()
        if slide:
            s.delete(slide)


def get_slide_by_id(slide_id: int, owner_id: int) -> dict | None:
    """
    Retrieve a slide by its ID and owner ID.
    Returns a dict or None if not found or not owned by the user.
    """
    with session_scope() as s:
        slide = s.query(Slide).filter_by(id=slide_id, owner_id=owner_id).first()
        if slide:
            return model_to_dict(slide)
        return None


def get_slides(owner_id: int) -> list:
    """
    Retrieve all Slide entries associated with a specific user ID.
    """
    with session_scope() as s:
        slides = (
            s.query(Slide)
            .filter_by(owner_id=owner_id)
            .order_by(Slide.created_at.desc())
            .all()
        )
        return [model_to_dict(slide) for slide in slides]


def get_slide_by_name(name: str, owner_id: int) -> dict | None:
    """
    Retrieve a slide by its name and owner ID.
    Returns a dict or None if not found.
    """
    with session_scope() as s:
        slide = s.query(Slide).filter_by(name=name, owner_id=owner_id).first()
        if slide:
            return model_to_dict(slide)
        return None


# # Report operations
# def set_report(username: str, slide_id: int, report_text: str) -> dict:
#     """
#     Save a Report entry associated with a specific Slide,
#     ensuring that the user owns the slide.
#     """
#     with session_scope() as s:
#         token = s.query(Token).filter_by(username=username).first()
#         if not token:
#             raise ValueError(f"User with username '{username}' not found")

#         slide = s.query(Slide).filter_by(
#             id=slide_id, owner_id=token.id).first()
#         if not slide:
#             raise ValueError(
#                 f"Slide with ID '{slide_id}' not found or does not belong to user '{username}'"
#             )

#         current_time = sys_utils.get_current_time(milliseconds=False)
#         report = Report(
#             slide_id=slide.id,
#             text=report_text,
#             created_at=current_time,
#         )
#         s.add(report)
#         s.flush()

#         return model_to_dict(report)


# def get_report(username: str, slide_id: int) -> dict:
#     """
#     Fetch the report for a given slide ID,
#     ensuring that the user owns the slide.
#     """
#     with session_scope() as s:
#         token = s.query(Token).filter_by(username=username).first()
#         if not token:
#             raise ValueError(f"User with username '{username}' not found")

#         slide = s.query(Slide).filter_by(
#             id=slide_id, owner_id=token.id).first()
#         if not slide:
#             raise ValueError(
#                 f"Slide with ID '{slide_id}' not found or does not belong to user '{username}'"
#             )

#         report = s.query(Report).filter_by(slide_id=slide.id).first()
#         return model_to_dict(report) if report else None


# def delete_report(username: str, report_id: int) -> None:
#     """
#     Delete a report by its ID,
#     ensuring that the user owns the slide the report belongs to.
#     """
#     with session_scope() as s:
#         token = s.query(Token).filter_by(username=username).first()
#         if not token:
#             raise ValueError(f"User with username '{username}' not found")

#         report = (
#             s.query(Report)
#             .join(Slide)
#             .filter(Slide.owner_id == token.id, Report.id == report_id)
#             .first()
#         )
#         if not report:
#             raise ValueError(
#                 f"Report with ID '{report_id}' not found or does not belong to user '{username}'"
#             )

#         s.delete(report)


# Models operations
# def get_models() -> list:
#     """
#     Retrieve all models stored in the Models table.
#     """
#     with session_scope() as s:
#         models = s.query(Model).all()
#         return [model_to_dict(model) for model in models]


def get_model(model_id: int) -> dict:
    """
    Retrieve a single model by its ID.
    """
    with session_scope() as s:
        model = s.query(Model).filter_by(id=model_id).first()
        if model:
            return model_to_dict(model)
        return {}


# Task operations
def get_task_by_id(task_id: int, user_id: int) -> dict | None:
    """
    Get a task by its internal ID, ensuring user owns the slide.
    """
    with session_scope() as s:
        task = (
            s.query(InferenceTask)
            .join(Slide)
            .filter(InferenceTask.id == task_id, Slide.owner_id == user_id)
            .first()
        )
        if task:
            return model_to_dict(task)
        return None


def update_task(task_id: int, user_id: int, **fields_to_update) -> dict | None:
    """
    Update a task by its internal ID, ensuring user owns the slide.
    """
    with session_scope() as s:
        task = (
            s.query(InferenceTask)
            .join(Slide)
            .filter(InferenceTask.id == task_id, Slide.owner_id == user_id)
            .first()
        )
        if not task:
            return None

        for key, value in fields_to_update.items():
            if hasattr(task, key):
                setattr(task, key, value)

        s.flush()
        return model_to_dict(task)


def update_task_by_inference_task_id(
    inference_task_id: str, **fields_to_update
) -> dict | None:
    """
    Update a task by its inference_task_id.
    Used by webhook callbacks and status updates.
    """
    with session_scope() as s:
        task = (
            s.query(InferenceTask)
            .filter_by(inference_task_id=inference_task_id)
            .first()
        )
        if not task:
            return None

        for key, value in fields_to_update.items():
            if hasattr(task, key):
                setattr(task, key, value)

        s.flush()
        return model_to_dict(task)


def get_tasks(
    user_id: int,
    state: str = None,
    limit: int = constants.Defaults.TASK_LIMIT,
    offset: int = constants.Defaults.TASK_OFFSET,
) -> list:
    """
    Get all tasks for a user with optional filtering.
    """
    with session_scope() as s:
        query = s.query(InferenceTask).join(Slide).filter(Slide.owner_id == user_id)

        # Apply state filter if provided
        if state:
            query = query.filter(InferenceTask.state == state)

        # Order by most recent first
        query = query.order_by(InferenceTask.created_at.desc())

        # Apply pagination
        query = query.limit(limit).offset(offset)

        tasks = query.all()
        return [model_to_dict(task) for task in tasks]


def get_tasks_by_slide(slide_id: int, user_id: int) -> list:
    """
    Get all tasks for a specific slide, ensuring user owns the slide.
    Returns empty list if slide not found or not owned.
    """
    with session_scope() as s:
        tasks = (
            s.query(InferenceTask)
            .join(Slide)
            .filter(InferenceTask.slide_id == slide_id, Slide.owner_id == user_id)
            .order_by(InferenceTask.created_at.desc())
            .all()
        )
        return [model_to_dict(task) for task in tasks]


def create_task(
    slide_id: int,
    user_id: int,
    inference_task_id: str,
    state: str = constants.TaskState.PENDING,
    confidence: float = constants.Defaults.CONFIDENCE,
    message: str = None,
) -> dict | None:
    """
    Create a new inference task.
    Returns the task dict or None if slide not found/not owned.
    """
    with session_scope() as s:
        # Verify slide exists and is owned by user
        slide = s.query(Slide).filter_by(id=slide_id, owner_id=user_id).first()
        if not slide:
            return None

        task = InferenceTask(
            inference_task_id=inference_task_id,
            slide_id=slide_id,
            user_id=user_id,
            state=state,
            confidence=confidence,
            message=message,
            created_at=sys_utils.get_utc_timestamp(),
        )
        s.add(task)
        s.flush()
        return model_to_dict(task)
