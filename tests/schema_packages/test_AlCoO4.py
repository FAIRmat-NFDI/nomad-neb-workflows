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
import os.path

from nomad.utils import get_logger

from electronicparsers.vasp import VASPParser

from nomad_neb_workflows.schema_packages.neb import NEBWorkflow
from nomad import infrastructure

infrastructure.setup()

logger = get_logger(__name__)


def test_workflow_archive_yaml():
    input1 = 'tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/00/OUTCAR'
    input2 = os.path.join('tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/01', 'OUTCAR')
    input3 = os.path.join('tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/02', 'OUTCAR')
    input4 = os.path.join('tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/03', 'OUTCAR')
    input5 = os.path.join('tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/04', 'OUTCAR')
    input6 = os.path.join('tests/data/AlCo2S4_uday_gajera/AlCo2S4/neb/05', 'OUTCAR')
    workflow_input = os.path.join(
        'tests/data', 'AlCo2S4_uday_gajera', 'workflow.archive.yaml'
    )

    upload_files = StagingUploadFiles(upload_id='NEB_testdata_AlCo2S4', create=True)
    upload = Upload(upload_id='NEB_testdata_AlCo2S4')
    context = ServerContext(upload=upload)

    archive0 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry0'),
    )
    archive1 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry1'),
    )
    archive2 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry2'),
    )
    archive3 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry3'),
    )
    archive4 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry4'),
    )
    archive5 = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='entry5'),
    )

    VASPParser().parse(input1, archive0, logger)
    VASPParser().parse(input2, archive1, logger)
    VASPParser().parse(input3, archive2, logger)
    VASPParser().parse(input4, archive3, logger)
    VASPParser().parse(input5, archive4, logger)
    VASPParser().parse(input6, archive5, logger)

    workflow_archive = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(
            upload_id=upload.upload_id, entry_id='workflow_AlCo2S4_entry'
        ),
    )

    ArchiveParser().parse(workflow_input, workflow_archive, logger)

    upload_files.write_archive('entry0', archive0.m_to_dict())
    upload_files.write_archive('entry1', archive1.m_to_dict())
    upload_files.write_archive('entry2', archive2.m_to_dict())
    upload_files.write_archive('entry3', archive3.m_to_dict())
    upload_files.write_archive('entry4', archive4.m_to_dict())
    upload_files.write_archive('entry5', archive5.m_to_dict())
    upload_files.write_archive('workflow_AlCo2S4_entry', workflow_archive.m_to_dict())

    neb_workflow = workflow_archive.workflow2
    neb_workflow.normalize(archive=workflow_archive, logger=logger)

    # Asserting that the workflow is correctly instantiated
    assert isinstance(neb_workflow, NEBWorkflow)

    # # Asserting the default workflow name
    # assert neb_workflow.name == 'NEB of AlCo2S4'

    # Checking if total energy differences can be extracted
    energy_differences = neb_workflow.results.get('total_energy_differences')
    assert energy_differences is not None
    assert len(energy_differences) == 6

    # Ensuring metadata entry is correctly assigned after normalization
    assert workflow_archive.metadata.entry_type == 'NEB Workflow'
    # assert workflow_archive.metadata.entry_name == 'NEB Calculation'

    # import json
    # with open('output_AlCo2S4.json', 'w') as f:
    #     json.dump(workflow_archive.m_to_dict(), f, indent=4)


test_workflow_archive_yaml()
