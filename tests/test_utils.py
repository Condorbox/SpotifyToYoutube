import utils


def test_sanitize_filename_replaces_invalid_chars():
    assert utils.sanitize_filename('a/b\\c:d*e?f"g_e%') == "a_b_c_d_e_f_g_e"


def test_sanitize_filename_collapses_underscores_and_strips_edges():
    assert utils.sanitize_filename("  hello   world  ") == "hello_world"


def test_sanitize_filename_removes_control_chars():
    assert utils.sanitize_filename("ab\x00cd") == "abcd"


def test_sanitize_filename_strips_leading_and_trailing_dots():
    assert utils.sanitize_filename("...hello...") == "hello"


def test_sanitize_filename_strips_mixed_dot_underscore_edges():
    assert utils.sanitize_filename("._hello_.") == "hello"


def test_sanitize_filename_returns_fallback_for_empty_string():
    assert utils.sanitize_filename("") == "track"


def test_sanitize_filename_returns_fallback_for_single_dot():
    assert utils.sanitize_filename(".") == "track"


def test_sanitize_filename_returns_fallback_for_double_dot():
    assert utils.sanitize_filename("..") == "track"


def test_sanitize_filename_returns_fallback_for_only_invalid_chars():
    # All chars become underscores, then get stripped → empty → fallback
    assert utils.sanitize_filename("///") == "track"


def test_sanitize_filename_custom_fallback_is_used():
    assert utils.sanitize_filename(".", fallback="unknown") == "unknown"


def test_sanitize_filename_custom_fallback_for_empty():
    assert utils.sanitize_filename("", fallback="audio") == "audio"


def test_sanitize_filename_clamps_to_max_length():
    long_name = "a" * (utils.MAX_SIZE_FILE_NAME_LIMIT + 50)
    result = utils.sanitize_filename(long_name)
    assert len(result) == utils.MAX_SIZE_FILE_NAME_LIMIT


def test_sanitize_filename_does_not_truncate_short_names():
    name = "Artist - Title"
    assert utils.sanitize_filename(name) == "Artist_-_Title"
    assert len(utils.sanitize_filename(name)) <= utils.MAX_SIZE_FILE_NAME_LIMIT


