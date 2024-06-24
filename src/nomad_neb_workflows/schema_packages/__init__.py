from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class NOMADNEBWorkflowsEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_neb_workflows.schema_packages.neb import m_package

        return m_package


nomad_neb_workflows_plugin = NOMADNEBWorkflowsEntryPoint(
    name='NOMADNEBWorkflows',
    description='Schema package plugin for the NOMAD NEB workflows definitions.',
)
