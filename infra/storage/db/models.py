from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Boolean, Float, Text, JSON, Index, text
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True)
    role = Column(String)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)

    audio_id = Column(String)
    manager_id = Column(Integer, ForeignKey("users.id"))
    client_id = Column(String, nullable=True)

    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    start_time = Column(DateTime(timezone=True))
    duration_sec = Column(Integer)

    status = Column(String)
    task_id = Column(String, nullable=True, index=True)

    provider = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True, index=True)
    direction = Column(String, nullable=True)
    from_number = Column(String, nullable=True)
    to_number = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    manager = relationship("User")
    turns = relationship("SpeakerTurn", back_populates="call")
    results = relationship("CheckResult", back_populates="call")

    __table_args__ = (
        Index(
            "ix_calls_provider_external_id",
            "provider",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )


class SpeakerTurn(Base):
    __tablename__ = "speaker_turns"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"))

    speaker = Column(String)
    text = Column(Text)

    t_start = Column(Float)
    t_end = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    call = relationship("Call", back_populates="turns")
    results = relationship("CheckResult", back_populates="speaker_turn")


class Check(Base):
    __tablename__ = "checks"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    description = Column(Text)

    scope = Column(String)
    type = Column(String)

    output_type = Column(String)

    weight = Column(Float, default=1.0)
    active = Column(Boolean, default=True)

    rule_config = Column(JSON, nullable=True)
    prompt = Column(Text, nullable=True)
    expected_format = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True, index=True)

    call_id = Column(Integer, ForeignKey("calls.id"))
    check_id = Column(Integer, ForeignKey("checks.id"))
    speaker_turn_id = Column(Integer, ForeignKey("speaker_turns.id"), nullable=True)

    value_boolean = Column(Boolean, nullable=True)
    value_score = Column(Float, nullable=True)
    value_category = Column(String, nullable=True)

    raw_response = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    call = relationship("Call", back_populates="results")
    check = relationship("Check")
    speaker_turn = relationship("SpeakerTurn", back_populates="results")


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)

    provider = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=True)
    external_id = Column(String, nullable=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=True)

    status = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    call = relationship("Call")
