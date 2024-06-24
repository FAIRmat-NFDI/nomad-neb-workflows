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

from typing import Optional, List, Tuple

from nomad import utils
from nomad.datamodel.context import ClientContext
from nomad.datamodel.datamodel import EntryArchive, EntryMetadata
from nomad.utils import generate_entry_id

LOGGER = utils.get_logger(__name__)


def get_archives(
    context: ClientContext,
    mainfile: str,
    upload_id: Optional[str] = None,
    keys: List[str] = [],
) -> Tuple[EntryArchive, Optional[dict]]:
    """Prepares a main archive and child archives for parsing."""
    main_archive = EntryArchive(
        m_context=context,
        metadata=EntryMetadata(
            upload_id=upload_id,
            mainfile=mainfile,
            entry_id=generate_entry_id(upload_id=upload_id, mainfile=mainfile),
        ),
    )
    child_archives = None
    for key in keys:
        child_archives = {
            key: EntryArchive(
                m_context=context,
                metadata=EntryMetadata(
                    upload_id=upload_id,
                    mainfile=mainfile,
                    mainfile_key=key,
                    entry_id=generate_entry_id(
                        upload_id=upload_id, mainfile=mainfile, mainfile_key=key
                    ),
                ),
            )
        }
    return main_archive, child_archives
