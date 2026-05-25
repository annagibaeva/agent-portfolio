from __future__ import annotations
from src.emailer import send_digest


class FakeSMTP:
    sent = []

    def __init__(self, host, port):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self):
        pass

    def login(self, user, pw):
        pass

    def send_message(self, msg):
        FakeSMTP.sent.append(msg)


def test_dry_run_does_not_send():
    FakeSMTP.sent.clear()
    sent = send_digest(subject="s", html="<p>x</p>", recipient="a@b.c",
                       smtp_host="h", smtp_port=587, smtp_user="u",
                       smtp_password="p", dry_run=True, smtp_cls=FakeSMTP)
    assert sent is False
    assert FakeSMTP.sent == []


def test_send_delivers_message():
    FakeSMTP.sent.clear()
    sent = send_digest(subject="s", html="<p>x</p>", recipient="a@b.c",
                       smtp_host="h", smtp_port=587, smtp_user="u",
                       smtp_password="p", dry_run=False, smtp_cls=FakeSMTP)
    assert sent is True
    assert len(FakeSMTP.sent) == 1
    assert FakeSMTP.sent[0]["Subject"] == "s"
