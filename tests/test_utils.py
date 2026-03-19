import utils


def test_sanitize_filename_replaces_invalid_chars():
    assert utils.sanitize_filename('a/b\\c:d*e?f"g_e%') == "a_b_c_d_e_f_g_e"


def test_sanitize_filename_collapses_underscores_and_strips_edges():
    assert utils.sanitize_filename("  hello   world  ") == "hello_world"


def test_sanitize_filename_removes_control_chars():
    assert utils.sanitize_filename("ab\x00cd") == "abcd"

