from .common import db, Field, auth
from pydal.validators import *
import datetime

db.define_table(
    "task",
    Field("title", requires=IS_NOT_EMPTY()),
    Field("description", requires=IS_NOT_EMPTY()),
    Field("date_created", "datetime", readable=False, writable=False, default=lambda:datetime.datetime.now()),
    Field("deadline", "datetime", default=None),
    Field("status", requires=IS_IN_SET(["pending", "ackowledged", "rejected", "completed", "failed"])),
    Field("created_by", "reference auth_user"),
    Field("assigned_to", "reference auth_user"),
    Field("created_by_name", default=None),
    Field("assigned_to_name", default=None),
)

db.define_table(
    "comment",
    Field("taskid", "reference task", readable=False, writable=False),
    Field("body", requires=IS_NOT_EMPTY(), default=None),
    Field("post_date", "datetime", readable=False, writable=False, default=lambda:datetime.datetime.now()),
    Field("author", "reference auth_user", readable=False, writable=False, default=lambda:auth.user_id),
)

db.define_table(
    "user_manager",
    Field("user_id", "reference auth_user", readable=False, writable=False),
    Field("manager_id","reference auth_user", readable=False, writable=False),
)

