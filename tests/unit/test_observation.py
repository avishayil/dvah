import pytest

from dvah.models.observation import Observation
from dvah.models.provenance import TrustLevel


@pytest.mark.unit
def test_observation_fields_and_frozen():
    obs = Observation(source="github:repo", trust=TrustLevel.UNTRUSTED_DATA, content={"a": 1})
    assert obs.source == "github:repo"
    assert obs.trust is TrustLevel.UNTRUSTED_DATA
    assert obs.content == {"a": 1}
    with pytest.raises(Exception):
        obs.source = "other"


@pytest.mark.unit
def test_observation_content_defaults_empty():
    obs = Observation(source="s", trust=TrustLevel.MEMORY)
    assert obs.content == {}
