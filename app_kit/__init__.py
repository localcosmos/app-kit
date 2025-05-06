import sys
import app_kit.taxonomy

# app-kit-taxonomy ("taxonomy") is a submodule of app-kit. It has been an installable pypi package earlier.
# to make it still work with the old code, we need to add it to sys.modules
# so that it can be imported as from taxonomy.
sys.modules['taxonomy'] = app_kit.taxonomy

__version__ = '1.0'