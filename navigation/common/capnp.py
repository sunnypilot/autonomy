import capnp
import os

# Load the schema
navigation = capnp.load(os.path.join(os.path.dirname(__file__), 'navigation.capnp'))
