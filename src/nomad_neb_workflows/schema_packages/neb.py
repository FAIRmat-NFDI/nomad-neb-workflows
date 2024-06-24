from typing import TYPE_CHECKING
import numpy as np

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
    name = Quantity(
        type=str, a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )
    message = Quantity(type=str)

    total_energy_differences = Quantity(
        type=np.float64,
        shape=['*'],
        unit='joule',
        description="""
        Total energy differences of the system configuration for each of the steps in the path
        """,
    )

    def __init__(self, m_def: Section = None, m_context: Context = None, **kwargs):
        super().__init__(m_def, m_context, **kwargs)
        # Set the name of the section
        self.name = self.m_def.name

    def extract_total_energy_differences(self):
        tot_energies = []
        for output in self.outputs:
            tot_energies.append(output.section.energy.total.value)
        return tot_energies

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # super().normalize(archive, logger)

        print('hello!')

        try:
            self.total_energy_differences = self.extract_total_energy_differences()
        except Exception:
            logger.error('Could not set `NEBWorkflow.total_energy_differences`.')

        try:
            archive.metadata.entry_type = 'NEB'
            archive.metadata.entry_name = 'name test'
        except Exception:
            logger.error(
                'Could not set archive.metadata quantities entry_type and entry_name.'
            )

        logger.info('MySchema.normalize', parameter=configuration.parameter)
        self.message = f'Hello {self.name}!'


m_package.__init_metainfo__()
