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

from atomisticparsers.utils import ASETrajParser

from nomad_neb_workflows.schema_packages.neb import NEBWorkflow
from nomad import infrastructure

infrastructure.setup()

logger = get_logger(__name__)


def test_workflow_archive_yaml():
    input1 = os.path.join('tests/data/NEB_testdata_Julia', 'neb0.traj')
    input2 = os.path.join('tests/data/NEB_testdata_Julia', 'neb1.traj')
    input3 = os.path.join('tests/data/NEB_testdata_Julia', 'neb6.traj')
    workflow_input = os.path.join(
        'tests/data', 'NEB_testdata_Julia', 'workflow1.archive.yaml'
    )

    upload_files = StagingUploadFiles(upload_id='NEB_testdata', create=True)
    upload = Upload(upload_id='NEB_testdata')
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

    ASETrajParser().parse(input1, ase_archive0, logger)
    ASETrajParser().parse(input2, ase_archive1, logger)
    ASETrajParser().parse(input3, ase_archive2, logger)

    workflow_archive = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(upload_id=upload.upload_id, entry_id='workflow_entry'),
    )

    ArchiveParser().parse(workflow_input, workflow_archive, logger)

    upload_files.write_archive('ase_entry0', ase_archive0.m_to_dict())
    upload_files.write_archive('ase_entry1', ase_archive1.m_to_dict())
    upload_files.write_archive('ase_entry2', ase_archive2.m_to_dict())
    upload_files.write_archive('workflow_entry', workflow_archive.m_to_dict())

    neb_workflow = workflow_archive.workflow2
    neb_workflow.normalize(archive=workflow_archive, logger=logger)

    # Asserting that the workflow is correctly instantiated
    assert isinstance(neb_workflow, NEBWorkflow)

    # Asserting the default workflow name
    assert neb_workflow.name == 'NEB of CH3-O on CuZn(211)'

    # Checking if total energy differences can be extracted
    energy_differences = neb_workflow.results.get('total_energy_differences')
    assert energy_differences is not None
    assert len(energy_differences) == 3

    # Ensuring metadata entry is correctly assigned after normalization
    assert workflow_archive.metadata.entry_type == 'NEB Workflow'
    assert workflow_archive.metadata.entry_name == 'NEB of CH3-O on CuZn(211)'

    # import json
    # with open('output_CuCuZn.json', 'w') as f:
    #     json.dump(workflow_archive.m_to_dict(), f, indent=4)
