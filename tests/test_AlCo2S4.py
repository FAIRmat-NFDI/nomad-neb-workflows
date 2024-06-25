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

from nomad_neb_workflows.schema_packages.neb import NEBWorkflow

from .conftest import LOGGER, server_context


def test_workflow_archive_yaml():
    mainfile = 'tests/data/AlCo2S4_uday_gajera/workflow.archive.yaml'
    # Adding context to the archive in order to resolve the references
    context = server_context(file=mainfile)
    archive = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(entry_id='test_entry', upload_id='test_upload'),
    )
    # Parsing the file
    ArchiveParser().parse(mainfile=mainfile, archive=archive, logger=LOGGER)

    serialized = archive.m_to_dict()
    deserialized = archive.m_from_dict(serialized, m_context=context)

    # Normalizing and asserting the workflow
    assert isinstance(archive.workflow2, NEBWorkflow)
    neb_workflow = archive.workflow2
    # TODO fix this! Ask Amir why this is not working
    neb_workflow.normalize(archive=archive, logger=LOGGER)
    assert neb_workflow.name == 'NEB'

    context.close()
