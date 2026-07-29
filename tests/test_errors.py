"""Error taxonomy tests."""

from questline.core.errors import (
    AssertionFailedError,
    AuthoringError,
    DeviceError,
    ElementNotFoundError,
    InfraError,
    ProviderError,
    QuestlineError,
    SessionLostError,
    TestError,
    TimeoutExceededError,
    Verdict,
    classify,
)


def test_classify_matrix() -> None:
    assert classify(SessionLostError(kind="ws", close_code=1006)) == Verdict.INFRA
    assert classify(DeviceError("adb failed")) == Verdict.INFRA
    assert classify(ProviderError("rate limit")) == Verdict.INFRA
    assert classify(InfraError("broker")) == Verdict.INFRA
    assert classify(ElementNotFoundError("btn")) == Verdict.TEST
    assert classify(AssertionFailedError("1 != 2")) == Verdict.TEST
    assert classify(TimeoutExceededError(kind="probe")) == Verdict.TEST
    assert classify(TestError("nope")) == Verdict.TEST
    assert classify(AuthoringError("bad marker")) == Verdict.AUTHORING
    assert classify(QuestlineError("other")) == Verdict.UNKNOWN
    assert classify(ValueError("stdlib")) == Verdict.UNKNOWN


def test_session_lost_fields() -> None:
    err = SessionLostError("gone", kind="socket", close_code=1006)
    assert err.kind == "socket"
    assert err.close_code == 1006
    assert err.message == "gone"


def test_timeout_kind() -> None:
    err = TimeoutExceededError(kind="probe")
    assert err.kind == "probe"
