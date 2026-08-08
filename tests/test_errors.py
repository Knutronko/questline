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
    normalize_exception,
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
    assert classify(AssertionError("plain assert")) == Verdict.TEST


def test_normalize_transport_signatures() -> None:
    wrapped = normalize_exception(ConnectionResetError("peer reset"))
    assert isinstance(wrapped, SessionLostError)
    assert wrapped.kind == "disconnect"
    assert classify(ConnectionResetError("peer reset")) == Verdict.INFRA

    no_app = normalize_exception(RuntimeError("No app connected to server"))
    assert isinstance(no_app, SessionLostError)
    assert no_app.kind == "no_app"

    empty = normalize_exception(RuntimeError("empty hierarchy at teardown"))
    assert isinstance(empty, SessionLostError)
    assert empty.kind == "empty_hierarchy"

    orig = SessionLostError("x", kind="fault_inject", close_code=1006)
    assert normalize_exception(orig) is orig


def test_session_lost_fields() -> None:
    err = SessionLostError("gone", kind="socket", close_code=1006)
    assert err.kind == "socket"
    assert err.close_code == 1006
    assert err.message == "gone"


def test_timeout_kind() -> None:
    err = TimeoutExceededError(kind="probe")
    assert err.kind == "probe"
