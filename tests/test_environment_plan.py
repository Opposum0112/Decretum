from sec_agent.environment_plan import plan_environment

def test_provider_plan_is_schema_shaped():
    registry = {"providers": {"newvm": {
        "kind": "vm",
        "interface": {"type": "api", "endpoint": "local:newvm"},
        "capabilities": ["compute.vm"],
        "provisioning": {"installable": True, "executable": "newvm", "approval_required": True},
        "lifecycle": {"create": "create", "destroy": "destroy", "collect_before_destroy": True},
        "isolation": "vm", "network": "isolated", "supports_ephemeral": True,
    }}}
    recipe = {"environment": {"compute": {"provider": "newvm", "ephemeral": True},
                              "sandbox": {"backend": "unix"}}}
    plan = plan_environment(recipe, registry)
    assert plan["provider"] == "newvm"
    assert plan["lifecycle"]["destroy"] == "destroy"
    assert plan["provisioning"]["approval_required"] is False
