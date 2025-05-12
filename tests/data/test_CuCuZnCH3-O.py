#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from nomad.parsing.parser import ArchiveParser
from nomad.datamodel import EntryArchive, EntryMetadata
from nomad.datamodel.context import ServerContext, ClientContext
from nomad.files import StagingUploadFiles
from nomad.processing import Upload
import sys
from nomad.utils import get_logger

from atomisticparsers.utils import ASETrajParser

from nomad_neb_workflows.schema_packages.neb import NEBWorkflow
from nomad import infrastructure

infrastructure.setup()

#from conftest import LOGGER, get_archives

logger = get_logger(__name__)

upload_files = StagingUploadFiles(upload_id='NEB_testdata_Julia', create=True)
upload = Upload(upload_id='NEB_testdata_Julia')
context = ServerContext(upload=upload)

ase_archive0 = EntryArchive(
    m_context=context,
    metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='ase_entry0'),
)
ase_archive1 = EntryArchive(
    m_context=context,
    metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='ase_entry1'),
)
ase_archive2 = EntryArchive(
    m_context=context,
    metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='ase_entry2'),
)

ASETrajParser().parse(sys.argv[-3], ase_archive0, logger)
ASETrajParser().parse(sys.argv[-2], ase_archive1, logger)
ASETrajParser().parse(sys.argv[-1], ase_archive2, logger)

workflow_archive = EntryArchive(
    m_context=context,
    metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='workflow_entry'),
)

ArchiveParser().parse(sys.argv[-4], workflow_archive, logger)

upload_files.write_archive('ase_entry0', ase_archive0.m_to_dict())
upload_files.write_archive('ase_entry1', ase_archive1.m_to_dict())
upload_files.write_archive('ase_entry2', ase_archive2.m_to_dict())
upload_files.write_archive('workflow_entry', workflow_archive.m_to_dict())

neb_workflow = workflow_archive.workflow2
    # Normalizing the workflow
neb_workflow.normalize(archive=workflow_archive, logger=logger)

import json
with open('output.json', 'w') as f:
    json.dump(workflow_archive.m_to_dict(), f, indent=4)

# def test_workflow_archive_yaml():
#     mainfile = 'tests/data/NEB_testdata_Julia/workflow_5.archive.yaml'

#     # Generating an archive with context to resolve referenced sections
#     archive, _ = get_archives(context=ClientContext(), mainfile=mainfile)

#     # Parsing the file
#     ArchiveParser().parse(mainfile=mainfile, archive=archive, logger=LOGGER)

#     # Asserting that the workflow is correctly instantiated
#     assert isinstance(archive.workflow2, NEBWorkflow)
#     neb_workflow = archive.workflow2
#     print('workflow2:', neb_workflow)
#     # Normalizing the workflow
#     neb_workflow.normalize(archive=archive, logger=LOGGER)
#     print('normalizing workflow')
#     # Asserting the default workflow name
#     assert neb_workflow.name == 'NEB'

#     # Checking if total energy differences can be extracted
#     energy_differences = neb_workflow.extract_total_energy_differences(logger=LOGGER)
#     assert energy_differences is None or isinstance(energy_differences, list)

#     # Ensuring metadata entry is correctly assigned after normalization
#     assert archive.metadata.entry_type == 'NEB'
#     assert archive.metadata.entry_name == 'NEB test'

#     # Attempting to plot the energy profile (should not raise exceptions)
#     try:
#         neb_workflow.plot_energy_vs_position(logger=LOGGER)
#     except Exception as e:
#         assert False, f'plot_energy_vs_position raised an exception: {e}'
