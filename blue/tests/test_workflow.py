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
    env = {**PACKAGE_SECRETS, "COLORS_PAR_NO_INFRA_SMTP_PASSWORD": "x", "COLORS_PAR_DO_TOKEN": "x"}
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
        ["vaultwarden/compute"]
    assert list(workflow.wire_fn("vaultwarden/start", fixture({"blue/event": "delete"}))[1:]) == \
        ["vaultwarden/github"]
    assert list(workflow.wire_fn("vaultwarden/dns", {"blue/event": "delete"})[1:]) == \
        ["vaultwarden/smtp"]


def test_official_image_omits_github_from_the_graph():
    opts = without(fixture(), "vaultwarden-repo")
    assert list(workflow.wire_fn("vaultwarden/ansible-remote",
                                 {**opts, "blue/event": "create"})[1:]) == []
    assert list(workflow.wire_fn("vaultwarden/start",
                                 {**opts, "blue/event": "delete"})[1:]) == \
        ["vaultwarden/ansible-cleanup"]


async def test_delete_inspection_refuses_unrecorded_inventory(monkeypatch):
    from package_vaultwarden_blue import machine
    seen = []
    async def inspect(opts, env):
        seen.append(env)
        return {'status': 'absent'}
    monkeypatch.setattr(machine, 'read_deployment', inspect)
    result = await machine.load(fixture({'ip': '203.0.113.99'}), {'AWS_PROFILE': 'fixture'})
    assert result['blue/exit'] == 1
    assert 'inventory unavailable' in result['blue/err']
    assert seen == [{'AWS_PROFILE': 'fixture'}]


async def test_local_ssh_uses_recorded_node_and_profile(monkeypatch):
    from package_vaultwarden_blue import tools
    async def run(opts, specs, **config):
        hosts = config['extra_vars']['ssh_hosts']
        assert hosts == [{'name': 'vaultwarden-fixture', 'ip': '203.0.113.8',
                          'user': 'ubuntu', 'identity_file': '/tmp/external'}]
        assert config['extra_vars']['block_state'] == 'absent'
        return opts
    monkeypatch.setattr(tools, 'ansible_with_spec', run)
    await tools.ansible_local_step(fixture({'blue/event': 'delete', 'once/compute-params': {
        'name': 'cloud-label', 'ip': '203.0.113.8', 'user': 'ubuntu', 'ssh-private-key-path': '/tmp/external'}}))


def test_compute_step_and_legacy_guard_use_direct_library():
    from package_vaultwarden_blue import machine
    assert workflow.wire_fn('vaultwarden/compute', {'blue/event': 'create'}) == (machine.step, 'vaultwarden/smtp')
    assert machine.requirements(fixture())['legacy_state_keys'] == ['vaultwarden-fixture/tofu-compute.tfstate']
    assert machine.errors(fixture({'provider-compute': 'no-infra'}))
    assert machine.errors(fixture({'compute-http-sources': []}))
