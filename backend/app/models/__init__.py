"""
Studable API — SQLAlchemy ORM models package.

All model modules must be imported here so that:
  1. Alembic's autogenerate can discover every table.
  2. SQLAlchemy's relationship() back-references resolve without circular imports.

Import order: User first (referenced by all others), then supporting tables.
"""

from app.models.user import User, UserInterest, UserSkill, UserLanguage  # noqa: F401
from app.models.auth import RefreshToken                                   # noqa: F401
from app.models.connection import Connection                               # noqa: F401
from app.models.conversation import Conversation                           # noqa: F401
from app.models.message import Message                                     # noqa: F401
from app.models.notification import Notification                           # noqa: F401
from app.models.report import Report                                       # noqa: F401
from app.models.block import Block                                         # noqa: F401
from app.models.match_request import MatchRequest                          # noqa: F401
