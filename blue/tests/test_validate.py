from conftest import fixture, without
from package_vaultwarden_blue import validate


def matching(opts, fragment):
    return [e for e in validate.state_errors(opts) if fragment in e]


def test_fixture_is_valid():
    assert validate.state_errors(fixture()) == []


def test_reports_all_invalid_fields():
    errors = validate.state_errors(fixture({
        "vaultwarden-host": "bad",
        "vaultwarden-repo": "bad",
        "vaultwarden-owner-email": "bad",
        "vaultwarden-signups-allowed": True,
        "vaultwarden-admin-enabled": True,
        "litestream-retention": "forever",
    }))
    assert len(errors) >= 6
    for fragment in ["host", "repo", "email", "signups", "admin", "retention"]:
        assert any(fragment in e for e in errors)


def test_image_must_be_pinned():
    assert matching(fixture({"vaultwarden-image": "ghcr.io/getcolors/vaultwarden"}),
                    "explicit tag")


def test_repository_is_optional_only_for_the_official_image():
    assert validate.state_errors(without(fixture(), "vaultwarden-repo")) == []
    assert matching(without(fixture({"vaultwarden-image": "ghcr.io/acme/vaultwarden:1.0.0"}),
                            "vaultwarden-repo"),
                    "repo is required")
    assert matching(fixture({"vaultwarden-repo": "acme/vaultwarden"}), "repo") == []


def test_restore_check_schedule_must_match_the_image():
    assert matching(fixture({"litestream-restore-check-oncalendar": "daily"}),
                    "one weekly")


def test_profile_overlay_is_refused():
    assert validate.PROFILE_PAR == "COLORS_PAR_PROFILE"
    assert validate.env_errors({"COLORS_PAR_PROFILE": "other"})
    assert validate.env_errors({}) == []


def test_package_secrets_are_named():
    errors = "\n".join(validate.secret_errors(fixture()))
    for par in ["COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID",
                "COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY",
                "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN"]:
        assert par in errors
