from conftest import fixture, without
from package_vaultwarden_blue import workflow

PACKAGE_SECRETS = {
    "COLORS_PAR_LITESTREAM_R2_ACCESS_KEY_ID": "x",
    "COLORS_PAR_LITESTREAM_R2_SECRET_ACCESS_KEY": "x",
    "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN": "x",
}


async def test_build_and_dry_run_need_no_credentials():
    assert (await workflow.start_step(fixture({"blue/event": "build"}), {}))["blue/exit"] == 0
    assert (await workflow.start_step(
        fixture({"blue/event": "create", "blue/dry-run": True}), {}))["blue/exit"] == 0


async def test_real_create_demands_package_and_provider_credentials():
    bare = await workflow.start_step(fixture({"blue/event": "create"}), {})
    assert bare["blue/exit"] == 2
    assert "COLORS_PAR_VAULTWARDEN_ADMIN_TOKEN" in bare["blue/err"]
    with_package = await workflow.start_step(fixture({"blue/event": "create"}), PACKAGE_SECRETS)
    assert with_package["blue/exit"] == 2
    assert "COLORS_PAR_NO_INFRA_SMTP_PASSWORD" in with_package["blue/err"]


async def test_official_image_needs_no_github_credential():
    env = {**PACKAGE_SECRETS, "COLORS_PAR_NO_INFRA_SMTP_PASSWORD": "x"}
    opts = without(fixture({"blue/event": "create"}), "vaultwarden-repo")
    result = await workflow.start_step(opts, env)
    assert result["blue/exit"] == 0
    assert "COLORS_PAR_GITHUB_TOKEN" not in str(result.get("blue/err") or "")


async def test_delete_is_protected():
    result = await workflow.start_step(fixture({"blue/event": "delete"}), {})
    assert result["blue/exit"] == 2
    assert "COMPUTE_PREVENT_DESTROY" in result["blue/err"]


def test_graph_reuses_once_stages_and_reverses_on_delete():
    assert list(workflow.wire_fn("vaultwarden/start", {"blue/event": "create"})[1:]) == \
        ["vaultwarden/compute", "vaultwarden/smtp"]
    assert list(workflow.wire_fn("vaultwarden/start", fixture({"blue/event": "delete"}))[1:]) == \
        ["vaultwarden/github"]
    assert list(workflow.wire_fn("vaultwarden/dns", {"blue/event": "delete"})[1:]) == \
        ["vaultwarden/smtp", "vaultwarden/compute"]


def test_official_image_omits_github_from_the_graph():
    opts = without(fixture(), "vaultwarden-repo")
    assert list(workflow.wire_fn("vaultwarden/ansible-remote",
                                 {**opts, "blue/event": "create"})[1:]) == []
    assert list(workflow.wire_fn("vaultwarden/start",
                                 {**opts, "blue/event": "delete"})[1:]) == \
        ["vaultwarden/ansible-cleanup"]
