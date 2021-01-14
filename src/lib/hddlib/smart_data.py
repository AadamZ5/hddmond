import strawberry
import datetime

from typing import List, Tuple
from pySMART import Device

@strawberry.type(description="Information about a specific attribute")
class AttributeData:
    index: int
    name: str
    flags: int
    raw_value: int
    threshold: int
    attr_type: str
    updated_freq: str
    value: int
    when_failed: str
    worst: int

@strawberry.type()
class TestCapability:
    test: str
    available: bool

@strawberry.type(description="S.M.A.R.T. information about a device")
class SmartCapture:
    capture_date: str
    attributes: List[AttributeData]
    firmware: str
    interface: str
    messages: List[str]
    smart_capable: bool
    smart_enabled: bool
    assessment: str
    test_capabilities: List[TestCapability]
    #tests: Test #Test type not implimented yet. We must rely on our database to hold this info. S.M.A.R.T. is skimpy here.

    @staticmethod
    def FromSmartDev(device: Device):
        formatted_attrs = []
        for a in device.attributes:
            if a != None:
                attr = AttributeData(a.num, a.name, a.flags, a.raw, a.thresh, a.type, a.updated, a.value, a.when_failed, a.worst)
                formatted_attrs.append(attr)
        
        test_capabilities = []
        for k in device.test_capabilities:
            t = TestCapability(str(k), device.test_capabilities[k])
            test_capabilities.append(t)
        s = SmartCapture(datetime.datetime.now(datetime.timezone.utc).isoformat(), formatted_attrs, device.firmware, device.interface, device.messages, device.smart_capable, device.smart_enabled, device.assessment, test_capabilities)
        return s
