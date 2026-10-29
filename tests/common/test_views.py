from datetime import datetime, timezone
from importlib import import_module

import pytest

from annetbox.common.models import Entity, InterfaceType, Vrf, vrf_object

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
VERSIONS = ["v37", "v41", "v42"]


class Version:
    def __init__(self, name: str):
        self.name = name
        self.api = import_module(f"annetbox.{name}.models")
        self.views = import_module(f"annetbox.{name}.views")

    def entity(self, id_: int = 1, name: str = "x"):
        return self.api.Entity(
            id=id_, name=name, display=name, url=f"/{name}/",
        )

    def tag(self):
        return self.api.EntityWithSlug(
            id=7, name="Tag", display="Tag", url="/tag/", slug="tag",
        )

    def vrf(self):
        kwargs = {
            "id": 3,
            "name": "mgmt",
            "display": "mgmt",
            "url": "/vrf/",
            "rd": "1:1",
        }
        if self.name != "v37":  # 3.7 VrfBrief has no description
            kwargs["description"] = "d"
        return self.api.VrfBrief(**kwargs)

    def prefix(self, *, site: bool = True):
        # 4.2 replaced `site` with `scope` and `scope_type`
        where = (
            {
                "scope_type": "dcim.site" if site else "dcim.location",
                "scope": self.entity(5, "ams"),
            }
            if self.name == "v42"
            else {"site": self.entity(5, "ams") if site else None}
        )
        return self.api.Prefix(
            id=1,
            prefix="10.0.0.0/24",
            vrf=self.vrf(),
            tenant=None,
            vlan=None,
            role=self.entity(2, "PTP Backbone"),
            tags=[self.tag()],
            status=self.api.Label(value="active", label="Active"),
            is_pool=False,
            custom_fields={},
            created=NOW,
            description="",
            last_updated=NOW,
            **where,
        )

    def device_ip(self):
        family = (
            4 if self.name == "v37"
            else self.api.IpFamily(value=4, label="IPv4")
        )
        return self.api.DeviceIp(
            id=9, display="10.0.0.254/24", address="10.0.0.254/24",
            family=family,
        )

    def fhrp_group(self):
        return self.api.FHRPGroup(
            id=10,
            group_id=1,
            display="vrrp",
            protocol="vrrp3",
            description="",
            name="vrrp",
            auth_type=None,
            auth_key="",
            tags=[self.tag()],
            custom_fields={},
            ip_addresses=[self.device_ip()],
            comments=None,
        )

    def fhrp_assignment(self):
        brief = {
            "id": 10, "group_id": 1, "display": "vrrp", "protocol": "vrrp3",
        }
        if self.name != "v37":  # 3.7 FHRPGroupBrief has no description
            brief["description"] = ""
        return self.api.FHRPGroupAssignmentBrief(
            id=11,
            display="assignment",
            priority=100,
            interface_type="dcim.interface",
            interface_id=5,
            group=self.api.FHRPGroupBrief(**brief),
        )

    def interface(self):
        cls = getattr(self.views, f"InterfaceV{self.name[1:]}")
        return cls(
            id=5,
            name="eth0",
            device=Entity(id=1, name="dev"),
            enabled=True,
            description="",
            type=InterfaceType(value="1000base-t", label="1000BASE-T"),
            connected_endpoints=[],
            mode=None,
            untagged_vlan=None,
            tagged_vlans=[],
        )

    def ip_address(self):
        return self.api.IpAddress(
            id=1,
            assigned_object_id=2,
            assigned_object=None,
            display="10.0.0.1/24",
            family=self.api.IpFamily(value=4, label="IPv4"),
            address="10.0.0.1/24",
            status=self.api.Label(value="active", label="Active"),
            role=None,
            tags=[self.tag()],
            created=NOW,
            last_updated=NOW,
            tenant=None,
            vrf=self.vrf(),
        )


@pytest.fixture(params=VERSIONS)
def version(request) -> Version:
    return Version(request.param)


def test_convert_prefixes(version):
    (prefix,) = version.views.convert_prefixes([version.prefix()])
    assert [(t.name, t.slug) for t in prefix.tags] == [("Tag", "tag")]
    assert prefix.vrf.name == "mgmt"
    assert prefix.vrf.rd == "1:1"
    assert prefix.vrf.description == (None if version.name == "v37" else "d")


def test_prefix_site(version):
    (prefix,) = version.views.convert_prefixes([version.prefix()])
    assert prefix.site == Entity(id=5, name="ams")
    (prefix,) = version.views.convert_prefixes([version.prefix(site=False)])
    assert prefix.site is None


def test_convert_ip_addresses(version):
    (ip,) = version.views.convert_ip_addresses([version.ip_address()])
    assert ip.prefix is None
    assert ip.address == "10.0.0.1/24"
    assert [t.slug for t in ip.tags] == ["tag"]
    assert ip.vrf.name == "mgmt"


def test_vrf_object():
    assert vrf_object(None) is None
    assert vrf_object("mgmt") == Vrf(
        id=0, name="mgmt", rd=None, description="",
    )


def test_convert_fhrp_groups(version):
    (group,) = version.views.convert_fhrp_groups([version.fhrp_group()])
    assert group.group_id == 1
    assert [t.slug for t in group.tags] == ["tag"]
    assert [ip.address for ip in group.ip_addresses] == ["10.0.0.254/24"]


def test_convert_fhrp_group_assignments(version):
    (assignment,) = version.views.convert_fhrp_group_assignments(
        [version.fhrp_assignment()],
    )
    # the group is filled in later, from the id
    assert assignment.group is None
    assert assignment.fhrp_group_id == 10
    assert assignment.interface_id == 5


def test_interface_add_addr(version):
    iface = version.interface()
    iface.add_addr("10.0.0.1/24", "mgmt")
    iface.add_addr("10.0.0.1/25", None)  # the same address, other mask
    iface.add_addr("2001:db8::1/64", None)
    assert [(a.address, a.family.value) for a in iface.ip_addresses] == [
        ("10.0.0.1/24", 4),
        ("2001:db8::1/64", 6),
    ]
    assert iface.ip_addresses[0].vrf.name == "mgmt"
    assert iface.ip_addresses[0].assigned_object_id == 5


def test_interface_set_vrf(version):
    iface = version.interface()
    iface.set_vrf("mgmt")
    assert iface.vrf.name == "mgmt"
    iface.set_vrf(None)
    assert iface.vrf is None
