from yardmaster.core.version import Version


def test_version_parse_three_part() -> None:
    v = Version.parse("1.2.3")
    assert (v.epoch, v.stream, v.revision) == (1, 2, 3)
    assert str(v) == "1.2.3"


def test_version_parse_default_revision() -> None:
    v = Version(epoch=1, stream=2)
    assert (v.epoch, v.stream, v.revision) == (1, 2, 0)
    assert str(v) == "1.2.0"
