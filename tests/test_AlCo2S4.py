import os

from nomad.client import parse
from nomad_neb_workflows.schema_packages.neb import NEBWorkflow

from . import LOGGER


def test_workflow_archive_yaml():
    filepath = os.path.join(
        os.path.dirname(__file__), 'data/AlCo2S4_uday_gajera/workflow.archive.yaml'
    )
    archives = parse(filepath)
    assert len(archives) == 1
    assert isinstance(archives[0].workflow2, NEBWorkflow)
    neb_workflow = archives[0].workflow2
    neb_workflow.normalize(archive=archives[0], logger=LOGGER)
    assert neb_workflow.name == 'NEBWorkflow'
    assert neb_workflow.message == 'Hello NEBWorkflow!'
