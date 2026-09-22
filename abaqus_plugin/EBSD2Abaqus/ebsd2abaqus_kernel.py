from abaqus import *
from abaqusConstants import *

import json
import os
import shutil
import subprocess


PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PLUGIN_DIR, 'backend')
TEMPLATE_CONFIG = os.path.join(PLUGIN_DIR, 'config.json')


def _ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def _run(command, cwd, env, log_handle, label):
    print '[EBSD2Abaqus] %s' % label
    log_handle.write(('\n[%s]\n%s\n' % (label, command)).encode('utf-8'))
    log_handle.flush()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        shell=True,
        stdout=log_handle,
        stderr=subprocess.STDOUT)
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(
            '%s failed with exit code %d. See conversion.log.'
            % (label, return_code))


def _quoted(path):
    return '"%s"' % path.replace('"', '')


def build_model(
        ctfFile='', projectFolder='', misorientationDeg=5.0,
        minGrainPixels=5):
    ctf_file = os.path.abspath(ctfFile.strip().strip('"'))
    project_folder = os.path.abspath(projectFolder.strip().strip('"'))

    if not os.path.isfile(ctf_file):
        raise RuntimeError('CTF file does not exist: %s' % ctf_file)
    if not ctf_file.lower().endswith('.ctf'):
        raise RuntimeError('Input file must use the .ctf extension.')
    if float(misorientationDeg) <= 0.0:
        raise RuntimeError('Misorientation must be greater than zero.')
    if int(minGrainPixels) < 1:
        raise RuntimeError('Minimum grain pixels must be at least one.')

    input_dir = os.path.join(project_folder, 'input')
    output_dir = os.path.join(project_folder, 'output')
    _ensure_dir(input_dir)
    _ensure_dir(output_dir)

    target_ctf = os.path.join(input_dir, 'ebsd.ctf')
    if os.path.normcase(ctf_file) != os.path.normcase(target_ctf):
        shutil.copy2(ctf_file, target_ctf)

    with open(TEMPLATE_CONFIG, 'r') as handle:
        config = json.load(handle)
    config['input_file'] = 'input/ebsd.ctf'
    config['grain_reconstruction']['misorientation_deg'] = float(
        misorientationDeg)
    config['grain_reconstruction']['min_grain_pixels'] = int(
        minGrainPixels)
    config_file = os.path.join(project_folder, 'config.json')
    with open(config_file, 'w') as handle:
        json.dump(config, handle, indent=2, sort_keys=True)

    env = os.environ.copy()
    env['EBSD2ABAQUS_PROJECT'] = project_folder

    matlab_script = os.path.join(BACKEND_DIR, 'export_ebsd.m')
    build_script = os.path.join(BACKEND_DIR, 'build_inp.py')
    import_script = os.path.join(BACKEND_DIR, 'import_cae.py')
    matlab_expr = "run('%s')" % matlab_script.replace('\\', '/').replace("'", "''")

    commands = [
        ('MTEX grain reconstruction', 'matlab -batch "%s"' % matlab_expr),
        ('Abaqus INP generation', 'python %s' % _quoted(build_script)),
        ('Abaqus CAE generation',
         'abaqus cae noGUI=%s' % _quoted(import_script)),
    ]

    log_path = os.path.join(project_folder, 'conversion.log')
    with open(log_path, 'wb') as log_handle:
        for label, command in commands:
            _run(command, project_folder, env, log_handle, label)

    cae_path = os.path.join(output_dir, config['model']['cae_name'])
    inp_path = os.path.join(output_dir, config['model']['inp_name'])
    if not os.path.isfile(cae_path):
        raise RuntimeError('CAE file was not created: %s' % cae_path)

    print '[EBSD2Abaqus] Completed.'
    print '  INP: %s' % inp_path
    print '  CAE: %s' % cae_path
    print '  Log: %s' % log_path
    return cae_path
