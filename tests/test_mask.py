"""`kubegap mask` strips terminal control characters from the report files, besides the credential patterns (#92)."""

from pathlib import Path

from lib.foundations import mask

ROOT = Path(__file__).resolve().parent.parent


def test_ansi_colour_sequences_are_removed_and_counted():
    r = mask.mask_text("a\x1b[31mred\x1b[0m b")
    assert r.text == "ared b" and r.counts == {"control-chars": 2}


def test_every_kind_of_control_sequence_is_removed_but_newline_and_tab_stay():
    cases = {
        "\x1b[2J\x1b[H": "",  # clear screen, home
        "\x1b]8;;http://evil.example\x07click here\x1b]8;;\x07": "click here",  # OSC 8 hyperlink, BEL-terminated
        "\x1b]0;title\x1b\\x": "x",  # OSC, ST-terminated
        "\x1b]0;unterminated": "",  # OSC without a terminator runs to the end of its line
        "pod \x1b]8;;http://x\x9c name tail": "pod  name tail",  # OSC ended by the 8-bit ST (ECMA-48 §8.3.143): the text after it stays (#128)
        "a \x9d8;;http://x\x9c b": "a  b",  # 8-bit OSC introducer (Table 2b) with its payload
        "a \x1bPq#0;2;0;0;0#0~~\x1b\\ b": "a  b",  # DCS (sixel) with its payload up to ST, 7-bit
        "a \x90payload\x9c b\x9fapc\x1b\\c\x1b_x\x1b\\d\x1b^pm\x1b\\e\x1bXsos\x9cf": "a  bcdef",  # DCS, APC, PM, SOS in both widths
        "a \x1b_unterminated apc\nnext line": "a \nnext line",  # a control string without ST ends at its line
        "a\x98sos\x9cb\x9epm\x9cc": "abc",  # 8-bit SOS and PM introducers
        "a\x9d0;t\x07b\x9d0;t\x1b\\c": "abc",  # 8-bit OSC ended by BEL and by the 7-bit ST
        "a\x1b]0;unterminated\nsecond line stays\nmore": "a\nsecond line stays\nmore",  # ... and never past it: the next lines stay
        "\x1bc\x1b(B\x1b=": "",  # RIS and the other Fe/Fs escapes are two bytes each
        "\x9b31m\x9b0mred": "red",  # 8-bit CSI
        "\x00\x07\x08\x0b\x0c\x0e\x1f\x7f": "",  # C0 and DEL
        "a\x85b\x8ec": "abc",  # lone C1 bytes (NEL, SS2); 0x9F is APC and opens a control string, see the cases above
        "line1\r\nline2\tcol": "line1\nline2\tcol",  # CR goes, LF and TAB stay
        "plain pod-name-7f9 ok": "plain pod-name-7f9 ok",
        "한글과 émoji 🙂 stay": "한글과 émoji 🙂 stay",
    }
    for src, want in cases.items():
        got = mask.mask_text(src)
        assert got.text == want, (src, got.text)
        assert ("control-chars" in got.counts) == (src != want), src


def test_control_chars_go_first_so_a_split_credential_is_still_masked():
    r = mask.mask_text("Authorization: Bea\x1b[0mrer abcdef.ghijkl")
    assert r.text == "Authorization: <masked>" and r.counts["control-chars"] == 1 and r.counts["bearer"] == 1


def test_mask_file_reports_control_chars(tmp_path):
    p = tmp_path / "report.md"
    p.write_text("# report\n\nevent: back-off \x1b[31mfailed\x1b[0m\n", encoding="utf-8")
    r = mask.mask_file(p)
    assert r.counts == {"control-chars": 2} and p.read_text(encoding="utf-8") == "# report\n\nevent: back-off failed\n"
    assert mask.mask_file(p).total == 0


def test_log_samples_pass_through_mask_text():
    """lib/foundations/logscan.py keeps the first 240 characters of a log line as a sample through mask_text, so a coloured log line arrives in summary.json without the colours."""
    src = (ROOT / "lib" / "foundations" / "logscan.py").read_text(encoding="utf-8")
    assert src.count("mask_text(line[:240]).text") == 2
