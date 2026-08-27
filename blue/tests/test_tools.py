from conftest import fixture, without
from package_vaultwarden_blue import tools


def test_adapter_builds_one_once_application():
    opts = tools.with_once_shape(fixture())
    app = opts["once"]["applications"][0]
    env = "\n".join(app["env"])
    assert app["host"] == "vault.example.com"
    assert app["image"] == "ghcr.io/getcolors/vaultwarden:1.0.0"
    assert app["github"] == "getcolors/vaultwarden"
    assert "DOMAIN=https://vault.example.com" in env
    assert "SIGNUPS_ALLOWED=false" in env
    assert "COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID" in env
    assert "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN" in env
    assert "secret-value" not in env


def test_adapter_omits_github_for_the_public_image():
    app = tools.with_once_shape(without(fixture(), "vaultwarden-repo"))["once"]["applications"][0]
    assert app["image"] == "ghcr.io/getcolors/vaultwarden:1.0.0"
    assert "github" not in app


def test_once_storage_path_is_fixed():
    assert "DATA_FOLDER=/storage" in tools.app_env(fixture())
