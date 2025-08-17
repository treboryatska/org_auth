"""
Basic jobs for the Dagster project.
These jobs orchestrate asset execution with different configurations.
"""

from dagster import job
from ..assets.assets import setup_hypergraph_schema_op

# run the setup hypergraph schema job
@job
def setup_hypergraph_job():
    """
    A one-time job to initialize the GRC-20 space and define the schema.
    """
    setup_hypergraph_schema_op()