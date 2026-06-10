"""Enums and Pydantic models for the Freshservice API."""

from enum import IntEnum, Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TicketSource(IntEnum):
    EMAIL = 1
    PORTAL = 2
    PHONE = 3
    YAMMER = 6
    CHAT = 7
    PAGERDUTY = 8
    WALK_UP = 9
    SLACK = 10
    WORKPLACE = 12
    EMPLOYEE_ONBOARDING = 13
    ALERTS = 14
    MS_TEAMS = 15
    EMPLOYEE_OFFBOARDING = 18


class TicketStatus(IntEnum):
    OPEN = 2
    PENDING = 3
    RESOLVED = 4
    CLOSED = 5


class TicketPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ChangeStatus(IntEnum):
    OPEN = 1
    PLANNING = 2
    AWAITING_APPROVAL = 3
    PENDING_RELEASE = 4
    PENDING_REVIEW = 5
    CLOSED = 6


class ChangePriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ChangeImpact(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ChangeType(IntEnum):
    MINOR = 1
    STANDARD = 2
    MAJOR = 3
    EMERGENCY = 4


class ChangeRisk(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class UnassignedForOptions(str, Enum):
    THIRTY_MIN = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    EIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    TWO_DAYS = "2d"
    THREE_DAYS = "3d"


class AgentInput(BaseModel):
    first_name: str = Field(..., description="First name of the agent")
    last_name: Optional[str] = Field(None, description="Last name of the agent")
    occasional: Optional[bool] = Field(False, description="True if the agent is an occasional agent")
    job_title: Optional[str] = Field(None, description="Job title of the agent")
    email: Optional[str] = Field(..., description="Email address of the agent")
    work_phone_number: Optional[int] = Field(None, description="Work phone number of the agent")
    mobile_phone_number: Optional[int] = Field(None, description="Mobile phone number of the agent")


class GroupCreate(BaseModel):
    name: str = Field(..., description="Name of the group")
    description: Optional[str] = Field(None, description="Description of the group")
    agent_ids: Optional[List[int]] = Field(
        default=None,
        description="Array of agent user ids",
    )
    auto_ticket_assign: Optional[bool] = Field(
        default=False,
        description="Whether tickets are automatically assigned",
    )
    escalate_to: Optional[int] = Field(
        None,
        description="User ID to whom escalation email is sent if ticket is unassigned",
    )
    unassigned_for: Optional[UnassignedForOptions] = Field(
        default=UnassignedForOptions.THIRTY_MIN,
        description="Time after which escalation email will be sent",
    )
