"""`kubegap config set`: one key written into config.yaml, the rest of the file left as the user wrote it."""

from __future__ import annotations

import stat

import pytest

from lib import configedit, yamlite
from lib.configedit import ConfigEditError, set_key, set_text


def test_new_file_gets_header_then_key(tmp_path):
    p = tmp_path / "config.yaml"
    diff, written = set_key(p, "ssh.hosts.node-a", "100.64.0.5")
    assert written and "+    node-a: 100.64.0.5" in diff
    text = p.read_text()
    assert text.startswith(configedit.HEADER)
    assert yamlite.load(text) == {"ssh": {"hosts": {"node-a": "100.64.0.5"}}}
    assert stat.S_IMODE(p.stat().st_mode) == 0o600


def test_dry_run_writes_nothing(tmp_path):
    p = tmp_path / "config.yaml"
    diff, written = set_key(p, "language", "ko", dry_run=True)
    assert diff and not written and not p.exists()


def test_same_value_is_no_change(tmp_path):
    p = tmp_path / "config.yaml"
    set_key(p, "mode", "full")
    assert set_key(p, "mode", "full") == ("", False)


def test_comments_and_order_survive():
    before = "# mine\nlanguage: en   # report language\n\nssh:\n  user: ubuntu\n  hosts:\n    a: 10.0.0.1\n\n# thresholds\noverrides:\n  x: 1\n"
    after = set_text(before, "ssh.hosts.b", "admin@10.0.0.2")
    assert after.splitlines() == ["# mine", "language: en   # report language", "", "ssh:", "  user: ubuntu", "  hosts:", "    a: 10.0.0.1", "    b: admin@10.0.0.2", "", "# thresholds", "overrides:", "  x: 1"]


def test_replaces_an_existing_value_and_adds_to_a_block():
    text = set_text("ssh:\n  user: a\n", "ssh.user", "b")
    assert yamlite.load(text) == {"ssh": {"user": "b"}}
    text = set_text(text, "ssh.accept_new_hosts", "true")
    assert yamlite.load(text) == {"ssh": {"user": "b", "accept_new_hosts": True}}
    text = set_text(text, "prometheus_url", "http://prom.example.internal:9090")
    assert yamlite.load(text)["prometheus_url"] == "http://prom.example.internal:9090"


def test_four_space_indent_is_followed():
    text = set_text("ssh:\n    user: a\n", "ssh.port", "2222")
    assert text == "ssh:\n    user: a\n    port: 2222\n"


def test_token_is_refused():
    with pytest.raises(ConfigEditError, match="yourself"):
        set_text("", "grafana_api_token", "glsa_x")


@pytest.mark.parametrize(
    ("key", "value"),
    [("language", "fr"), ("prometheus_url", "prom:9090"), ("ssh.port", "0"), ("ssh.hosts.bad name", "1.2.3.4"), ("ssh.hosts.a", "1.2.3.4 # x"), ("suppress", "x"), ("ssh.accept_new_hosts", "yes")],
)
def test_bad_key_or_value_is_refused(key, value):
    with pytest.raises(ConfigEditError):
        set_text("", key, value)


def test_layouts_the_editor_does_not_handle_say_so():
    with pytest.raises(ConfigEditError, match="by hand"):
        set_text("ssh: {user: a}\n", "ssh.user", "b")
    with pytest.raises(ConfigEditError, match="by hand"):
        set_text("ssh:\n  hosts:\n    a:\n      nested: 1\n", "ssh.hosts.a", "1.2.3.4")


def test_every_settable_key_is_a_known_config_key():
    from lib.config import KNOWN_KEYS

    assert {k.split(".")[0] for k in configedit.SETTABLE} | set(configedit.REFUSED) <= KNOWN_KEYS


def test_a_note_on_the_changed_line_stays():
    assert set_text("language: en   # report language\n", "language", "ko") == "language: ko  # report language\n"


def test_windows_line_ends_are_kept():
    assert set_text("language: en\r\nmode: daily\r\n", "mode", "full") == "language: en\r\nmode: full\r\n"


def test_text_that_yaml_reads_as_a_number_or_a_bool_is_quoted():
    assert yamlite.load(set_text("", "ssh.hosts.a", "12345")) == {"ssh": {"hosts": {"a": "12345"}}}
    assert yamlite.load(set_text("", "ssh.user", "true")) == {"ssh": {"user": "true"}}
    assert yamlite.load(set_text("", "ssh.port", "2222")) == {"ssh": {"port": 2222}}
    assert yamlite.load(set_text("", "ssh.accept_new_hosts", "true")) == {"ssh": {"accept_new_hosts": True}}


def test_a_block_followed_directly_by_a_top_level_key():
    assert set_text("ssh:\n  user: a\nmode: daily\n", "ssh.hosts.n", "10.0.0.1") == "ssh:\n  user: a\n  hosts:\n    n: 10.0.0.1\nmode: daily\n"


def test_a_linked_config_file_is_written_through_the_link(tmp_path):
    real = tmp_path / "dotfiles" / "kubegap.yaml"
    real.parent.mkdir()
    real.write_text("mode: daily\n")
    link = tmp_path / "config.yaml"
    link.symlink_to(real)
    set_key(link, "mode", "full")
    assert link.is_symlink() and real.read_text() == "mode: full\n"


def test_a_byte_order_mark_is_refused():
    with pytest.raises(ConfigEditError, match="byte order mark"):
        set_text("\ufefflanguage: en\n", "language", "ko")
