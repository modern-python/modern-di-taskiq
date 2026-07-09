import pytest
from modern_di import Container
from taskiq import InMemoryBroker

from modern_di_taskiq import setup_di
from tests.dependencies import Dependencies


@pytest.fixture
def broker() -> InMemoryBroker:
    broker_ = InMemoryBroker()
    setup_di(broker_, container=Container(groups=[Dependencies], validate=True))
    return broker_
