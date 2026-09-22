# Abaqus/CAE script: import the generated base INP and save a CAE database.
#
# Run from the project root with:
#   abaqus cae noGUI=scripts/import_cae.py

from abaqus import *
from abaqusConstants import *
import json
import os


try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.path.join(os.getcwd(), 'scripts')
ROOT_DIR = os.environ.get(
    'EBSD2ABAQUS_PROJECT', os.path.dirname(SCRIPT_DIR))
OUT_DIR = os.path.join(ROOT_DIR, 'output')
CONFIG_FILE = os.path.join(ROOT_DIR, 'config.json')

with open(CONFIG_FILE, 'r') as config_handle:
    CONFIG = json.load(config_handle)

# Abaqus 6.14 uses Python 2. Its CAE API rejects JSON unicode values even
# when they contain only ASCII characters, so convert them explicitly.
INP_FILE = os.path.join(OUT_DIR, str(CONFIG['model']['inp_name']))
CAE_FILE = os.path.join(OUT_DIR, str(CONFIG['model']['cae_name']))
MODEL_NAME = str(CONFIG['model']['model_name'])


if not os.path.exists(INP_FILE):
    raise RuntimeError('Cannot find input file: %s' % INP_FILE)

if MODEL_NAME in mdb.models.keys():
    del mdb.models[MODEL_NAME]

print('Importing %s' % INP_FILE)
mdb.ModelFromInputFile(name=MODEL_NAME, inputFileName=INP_FILE)

if 'Model-1' in mdb.models.keys():
    del mdb.models['Model-1']

if os.path.exists(CAE_FILE):
    os.remove(CAE_FILE)

print('Saving %s' % CAE_FILE)
mdb.saveAs(pathName=CAE_FILE)
print('Done.')
