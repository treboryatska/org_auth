# in dagster_project/io_managers.py
from dagster import IOManager, io_manager

class InMemoryIOManager(IOManager):
    def __init__(self):
        self.values = {}

    def handle_output(self, context, obj):
        # Store the asset's output in a dictionary in memory
        self.values[context.asset_key.to_string()] = obj

    def load_input(self, context):
        # Retrieve the stored output from the dictionary
        return self.values[context.asset_key.to_string()]

@io_manager
def in_memory_io_manager(_):
    return InMemoryIOManager()