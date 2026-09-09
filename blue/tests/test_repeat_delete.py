import pytest
from blue.workflow import run, workflow as graph
from package_vaultwarden_blue import machine, workflow

@pytest.mark.parametrize("status",["destroyed","absent","error"])
@pytest.mark.parametrize("event",["create","delete"])
async def test_inventory_retired_only_allows_delete(monkeypatch,tmp_path,status,event):
    async def read(*args):return {"status":status}
    monkeypatch.setattr(machine,"read_deployment",read)
    result=await machine.load({"blue/event":event,"workdir":str(tmp_path)})
    allowed=status=="destroyed" and event=="delete"
    assert result["blue/exit"]==(0 if allowed else 1)
    assert bool(result.get("colors-compute/already-destroyed"))==allowed
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize("retired,failure",[(True,False),(True,True),(False,False),(False,True)])
async def test_native_delete_short_circuit_and_cleanup_order(retired,failure):
    seen=[]
    def wire(step,opts):
        declared=workflow.wire_fn(step,opts)
        async def fake(current):
            seen.append(step)
            return {**current,"colors-compute/already-destroyed":retired,"blue/exit":1 if failure else 0}
        return (fake,*declared[1:]) if declared else None
    original=workflow.create_workflow()
    result=await run(graph(start="vaultwarden/start",wire_fn=wire,next_fn=original.next_fn),{"blue/event":"delete"})
    if retired or failure:assert seen==["vaultwarden/start"]
    else:assert seen[-3:]==["vaultwarden/dns","vaultwarden/smtp","vaultwarden/compute"]
    assert result["blue/exit"]==(1 if failure else 0)

async def test_retired_inventory_skips_smtp_state_read(monkeypatch):
    async def loaded(*args):return {'blue/exit':0,'colors-compute/already-destroyed':True}
    async def forbidden(*args):pytest.fail('retired deletion must not read SMTP state')
    monkeypatch.setattr(machine,'load',loaded)
    monkeypatch.setattr(workflow,'_state_output',forbidden)
    result=await workflow._adopt_existing_state({'blue/event':'delete'})
    assert result['colors-compute/already-destroyed'] is True

async def test_local_cleanup_failure_never_reaches_remote(monkeypatch):
    async def failure(opts):return {**opts,'blue/exit':1}
    async def forbidden(*args):pytest.fail('remote cleanup must not follow failed alias cleanup')
    monkeypatch.setattr(workflow.tools,'ansible_local_step',failure)
    monkeypatch.setattr(workflow.once_tools,'ansible_remote_step',forbidden)
    result=await workflow.ansible_cleanup_step({'blue/event':'delete'})
    assert result['blue/exit']==1
