# /opt/dagster/app/dagster_project/io_managers.py

from dagster import IOManager, io_manager

class InMemoryIOManager(IOManager):
    """
    A simple in-memory IO manager that stores outputs in a dictionary.
    This is suitable for development and testing, but not for production
    as it does not persist data across runs or processes.
    """
    def __init__(self):
        self._values = {}

    def handle_output(self, context, obj):
        """
        This method is called by Dagster to store an asset's output.
        We use the asset's key as the dictionary key.
        """
        key = context.asset_key.to_string()
        self._values[key] = obj
        context.log.info(f"Stored output for key: {key}")

    def load_input(self, context):
        """
        This method is called by Dagster to load an input for a downstream asset.
        We use the upstream asset's key to look up the value.
        """
        key = context.asset_key.to_string()
        context.log.info(f"Loading input for key: {key}")
        return self._values[key]

@io_manager
def in_memory_io_manager(_):
    return InMemoryIOManager()