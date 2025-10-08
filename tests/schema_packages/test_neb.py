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
import pathlib
import os.path
import shutil

import pytest
from nomad.client import normalize_all, parse

from nomad_neb_workflows.schema_packages.neb import NEBWorkflow

DATA_PATH = pathlib.Path(__file__).parent.parent / 'data'


def match_and_parse(filename, data_path, tmp_path):
    file_path = data_path / filename
    tmp_file = tmp_path / filename
    tmp_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file_path, tmp_file)
    return parse(tmp_file)[0]


@pytest.mark.usefixtures('tmp_path')
@pytest.mark.parametrize(
    'data_path, calculation_filenames, workflow_filename, workflow_name',
    [
        pytest.param(
            DATA_PATH / 'NEB_testdata_Julia',
            ['neb0.traj', 'neb1.traj', 'neb6.traj'],
            'workflow1.archive.yaml',
            'NEB of CH3-O on CuZn(211)',
            id='ASEtraj',
        ),
        pytest.param(
            DATA_PATH / 'AlCo2S4_uday_gajera',
            [os.path.join('AlCo2S4', 'neb', f'{i:02d}', 'OUTCAR') for i in range(6)],
            'workflow.archive.yaml',
            'NEB of Al7Co16S32',
            id='VASP',
        ),
    ],
)
def test_neb(
    tmp_path, data_path, calculation_filenames, workflow_filename, workflow_name
):
    calculation_entries = [
        match_and_parse(filename, data_path, tmp_path)
        for filename in calculation_filenames
    ]
    for entry in calculation_entries:
        normalize_all(entry)

    workflow_entry = match_and_parse(workflow_filename, data_path, tmp_path)
    neb_workflow = workflow_entry.workflow2
    assert isinstance(neb_workflow, NEBWorkflow)

    neb_workflow.inputs[0].section = calculation_entries[0]
    neb_workflow.inputs[1].section = calculation_entries[-1]
    for idx, entry in enumerate(calculation_entries[1:-1]):
        neb_workflow.tasks[idx].section = entry

    normalize_all(workflow_entry)

    # Asserting the default workflow name
    assert neb_workflow.name == workflow_name

    # Checking if total energy differences can be extracted
    energy_differences = neb_workflow.results.get('total_energy_differences')
    assert energy_differences is not None
    assert len(energy_differences) == len(calculation_entries)
