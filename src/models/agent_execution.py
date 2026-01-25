from sqlalchemy import Column, Integer, String, Enum, JSON
import enum
from .base import Base, TimestampMixin


class AgentStatus(enum.Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentExecution(Base, TimestampMixin):
    """Agent execution history model"""
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True)
    agent_name = Column(String(100), nullable=False)
    task_type = Column(String(100))
    input_data = Column(JSON)
    output_data = Column(JSON)
    status = Column(Enum(AgentStatus), default=AgentStatus.PENDING)
    execution_time_ms = Column(Integer)
    error_message = Column(String(1000))
