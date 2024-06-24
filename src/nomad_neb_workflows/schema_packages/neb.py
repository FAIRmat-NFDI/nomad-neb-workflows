from typing import TYPE_CHECKING, Optional
import numpy as np
import pint

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.metainfo import Quantity, SchemaPackage, Context, Quantity, Section
from simulationworkflowschema import SimulationWorkflow

configuration = config.get_plugin_entry_point(
    'nomad_neb_workflows.schema_packages:nomad_neb_workflows_plugin'
)

m_package = SchemaPackage()


class NEBWorkflow(SimulationWorkflow):
    """
    A base section used to define Nudged Elastic Band (NEB) workflows. These workflows are used to find the
    minimum energy path and transition states between two stable states in a system. It involves interpolating
    a series of intermediate configurations (or images) between the initial and final states, and then optimize
    these images to trace the most energetically favorable path.

    This workflow is useful to extract reactivities and catalytic properties, energy barriers, etc.
    """

    name = Quantity(
        type=str,
        default='NEB',
        description='Name of the workflow. Default set to `NEB`.',
    )

    total_energy_differences = Quantity(
        type=np.float64,
        shape=['*'],
        unit='joule',
        description="""
        Total energy differences of the system for each of the images in the path. These quantities are
        defined positive.
        """,
    )

    def extract_total_energy_differences(
        self, logger: 'BoundLogger'
    ) -> Optional[pint.Quantity]:
        """
        Extracts the total energy differences from the task outputs of the NEB workflow.

        Args:
            logger (BoundLogger): The logger to log messages.

        Returns:
            Optional[pint.Quantity]: The total energy differences of the system for each of the images in the path of configurations in units of energies.
        """
        # Resolve the reference of energies from the first NEB task
        scf_task = self.tasks[1]
        if scf_task.m_xpath('outputs[0].section.energy.total.value') is None:
            logger.error(
                'Could not resolved the initial value of the total energy for referencing.'
            )
            return None
        energy_reference = scf_task.outputs[0].section.energy.total.value.m
        energy_units = scf_task.outputs[0].section.energy.total.value.u

        # Append the energy differences of the images w.r.t. the reference of energies
        tot_energies = []
        for output in self.outputs:
            if output.section.energy.total.value.m - energy_reference < 0:
                logger.error(
                    'The total energy differences of any image must be positive.'
                )
                return None
            tot_energies.append(output.section.energy.total.value.m - energy_reference)
        return tot_energies * energy_units

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        try:
            self.total_energy_differences = self.extract_total_energy_differences(
                logger=logger
            )
        except Exception:
            logger.error('Could not set `NEBWorkflow.total_energy_differences`.')

        try:
            # TODO improve this naming
            archive.metadata.entry_type = 'NEB'
            archive.metadata.entry_name = 'NEB test'
        except Exception:
            logger.error(
                'Could not set archive.metadata quantities entry_type and entry_name.'
            )


m_package.__init_metainfo__()
