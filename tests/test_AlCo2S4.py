import os
from nomad.datamodel.datamodel import EntryArchive
from nomad_neb_workflows.schema_packages.neb import NEBWorkflow
from nomad.client import normalize_all, parse

from . import LOGGER


def test_workflow_archive_yaml():
    filepath = os.path.join(
        os.path.dirname(__file__), 'data/AlCo2S4_uday_gajera/workflow.archive.yaml'
    )
    archives = parse(filepath)
    assert len(archives) == 1
    archive = archives[0]
    normalize_all(archive)
    assert archive.workflow2
