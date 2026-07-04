"""Тесты данных модуля BRUTEFORCE (симуляция)."""

from ctos import bruteforce_config as C


def test_networks_have_ssid_and_signal():
    for n in C.NETWORKS:
        assert "ssid" in n
        assert "signal" in n


def test_exactly_one_lab_target():
    targets = [n for n in C.NETWORKS if n.get("target")]
    assert len(targets) == 1


def test_dict_profiles_complete():
    for key, prof in C.DICT_PROFILES.items():
        assert "max_attempts" in prof
        assert "delay_ms" in prof
        assert "label" in prof
        assert int(prof["max_attempts"]) > 0
        assert int(prof["delay_ms"]) > 0
    assert C.DEFAULT_PROFILE in C.DICT_PROFILES


def test_get_profile_fallback():
    p = C.get_profile("nonexistent_key_xyz")
    assert p == C.DICT_PROFILES[C.DEFAULT_PROFILE]


def test_handshake_phases_non_empty():
    assert len(C.HANDSHAKE_PHASES) >= 2


def test_fail_reasons_non_empty():
    assert len(C.FAIL_REASONS_NON_TARGET) >= 1


def test_target_password_nonempty():
    assert len(C.TARGET_PASSWORD) >= 4


def test_education_append_present():
    assert "SIMULATION" in C.EDUCATION_APPEND.upper()


def test_info_pages_tour():
    assert len(C.INFO_PAGES) >= 6
    keys = [p[0] for p in C.INFO_PAGES]
    assert "FINAL" in keys
    assert len(C.INFO_FINAL_THEORY) > 40
