import datetime as dt

from ninja import Schema


class LogOut(Schema):
    at: dt.datetime
    actor_name: str
    action: str
    detail: str

    @staticmethod
    def resolve_at(obj):
        return obj.created_at

    @staticmethod
    def resolve_actor_name(obj):
        return obj.actor.shown_name
