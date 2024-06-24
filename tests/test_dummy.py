from nomad.datamodel.datamodel import EntryArchive
from nomad_neb_workflows.schema_packages.neb import NEBWorkflow

from .conftest import LOGGER


def test_dummy():
    neb_workflow = NEBWorkflow(name='NEBWorkflow')
    neb_workflow.normalize(EntryArchive(), logger=LOGGER)
    assert neb_workflow.name == 'NEBWorkflow'
    assert neb_workflow.message == 'Hello NEBWorkflow!'
