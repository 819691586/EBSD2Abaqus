from __future__ import print_function

"""Build a neutral Abaqus INP from MTEX EBSD exports.

Compatible with both Python 2.7 (Abaqus 6.14) and Python 3.
The generated model contains geometry, mesh, sets, sections and per-grain
orientation/material constants. It contains no analysis step, load, crack,
XFEM definition or damage model.
"""

import csv
import json
import os


DEFAULT_OUTPUT_NAME = 'ebsd_base_model.inp'
PART_NAME = 'EBSD_CP'
INSTANCE_NAME = 'EBSD_CP-1'


def read_meta(path):
    with open(path, 'r') as handle:
        reader = csv.DictReader(handle)
        return dict((row['key'], row['value']) for row in reader)


def read_grain_props(path):
    result = {}
    with open(path, 'r') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            gid = int(float(row['GrainID']))
            result[gid] = {
                'phase': row.get('Phase', 'Ti-Hex'),
                'phi1': float(row['phi1']),
                'Phi': float(row['Phi']),
                'phi2': float(row['phi2']),
                'size': float(row['EquivalentDiameter_model']),
                'pixels': float(row['GrainSizePixels']),
            }
    return result


def read_grid(path):
    grid = []
    with open(path, 'r') as handle:
        for row in csv.reader(handle):
            if row:
                grid.append([int(float(value)) for value in row])
    return grid


def node_id(i, j, nx):
    return j * (nx + 1) + i + 1


def elem_id(i, j, nx):
    return j * nx + i + 1


def fmt_float(value):
    return '%.12g' % value


def write_label_set(handle, keyword, name, labels, per_line=16):
    handle.write('*%s, %s=%s\n' % (keyword, keyword.lower(), name))
    for start in range(0, len(labels), per_line):
        handle.write(', '.join(
            str(value) for value in labels[start:start + per_line]) + '\n')


def write_float_lines(handle, values, per_line=8):
    for start in range(0, len(values), per_line):
        handle.write(', '.join(
            fmt_float(value) for value in values[start:start + per_line]) + '\n')


def validate(meta, grid, grains):
    nx = int(float(meta['nx']))
    ny = int(float(meta['ny']))
    if len(grid) != ny:
        raise ValueError(
            'Grid row count mismatch: expected %d, read %d' % (ny, len(grid)))
    bad_rows = [index + 1 for index, row in enumerate(grid) if len(row) != nx]
    if bad_rows:
        raise ValueError('Grid column count mismatch in rows: %s' % bad_rows[:10])
    missing = sorted(set(
        gid for row in grid for gid in row if gid not in grains))
    if missing:
        raise ValueError('Grid references missing grains: %s' % missing[:20])
    return nx, ny


def build_inp(output_path, meta, grid, grains, element_type,
              depvar_count, umat_prefix, umat_suffix):
    nx, ny = validate(meta, grid, grains)
    dx = float(meta['dx_um']) * float(meta['model_scale'])
    dy = float(meta['dy_um']) * float(meta['model_scale'])

    grain_elements = {}
    for j, row in enumerate(grid):
        for i, gid in enumerate(row):
            grain_elements.setdefault(gid, []).append(elem_id(i, j, nx))

    left_nodes = [node_id(0, j, nx) for j in range(ny + 1)]
    right_nodes = [node_id(nx, j, nx) for j in range(ny + 1)]
    bottom_nodes = [node_id(i, 0, nx) for i in range(nx + 1)]
    top_nodes = [node_id(i, ny, nx) for i in range(nx + 1)]

    with open(output_path, 'w') as handle:
        handle.write('*Heading\n')
        handle.write('** Neutral EBSD voxel model for Abaqus\n')
        handle.write('** Source: %s\n' % meta.get('source_file', ''))
        handle.write(
            '** Grid: %d x %d pixels, dx=%s, dy=%s model units\n'
            % (nx, ny, fmt_float(dx), fmt_float(dy)))
        handle.write('** Retained grains: %d\n' % len(grains))
        handle.write('** No analysis step, load, crack, XFEM or damage model.\n')
        handle.write('*Preprint, echo=NO, model=NO, history=NO, contact=NO\n')
        handle.write('*Part, name=%s\n' % PART_NAME)

        handle.write('*Node\n')
        for j in range(ny + 1):
            y_value = j * dy
            for i in range(nx + 1):
                x_value = i * dx
                handle.write('%d, %s, %s\n' % (
                    node_id(i, j, nx), fmt_float(x_value), fmt_float(y_value)))

        handle.write('*Element, type=%s\n' % element_type)
        for j in range(ny):
            for i in range(nx):
                handle.write('%d, %d, %d, %d, %d\n' % (
                    elem_id(i, j, nx),
                    node_id(i, j, nx),
                    node_id(i + 1, j, nx),
                    node_id(i + 1, j + 1, nx),
                    node_id(i, j + 1, nx)))

        write_label_set(handle, 'Nset', 'LEFT', left_nodes)
        write_label_set(handle, 'Nset', 'RIGHT', right_nodes)
        write_label_set(handle, 'Nset', 'BOTTOM', bottom_nodes)
        write_label_set(handle, 'Nset', 'TOP', top_nodes)
        write_label_set(
            handle, 'Elset', 'ALL_ELEMENTS', list(range(1, nx * ny + 1)))

        for gid in sorted(grain_elements):
            write_label_set(
                handle, 'Elset', 'GRAIN_%04d' % gid,
                grain_elements[gid])

        for gid in sorted(grain_elements):
            handle.write(
                '*Solid Section, elset=GRAIN_%04d, material=M%04d\n'
                % (gid, gid))
            handle.write(',\n')

        handle.write('*End Part\n')
        handle.write('*Assembly, name=Assembly\n')
        handle.write('*Instance, name=%s, part=%s\n' % (INSTANCE_NAME, PART_NAME))
        handle.write('*End Instance\n')
        handle.write('*End Assembly\n')

        for gid in sorted(grains):
            grain = grains[gid]
            constants = (
                list(umat_prefix)
                + [grain['phi1'], grain['Phi'], grain['phi2']]
                + list(umat_suffix)
                + [grain['size']])
            handle.write('*Material, name=M%04d\n' % gid)
            handle.write('*Depvar\n')
            handle.write('%d,\n' % depvar_count)
            handle.write(
                '*User Material, constants=%d, unsymm\n' % len(constants))
            write_float_lines(handle, constants)

    return nx, ny


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_project_dir = os.path.dirname(script_dir)
    project_dir = os.path.abspath(os.environ.get(
        'EBSD2ABAQUS_PROJECT', default_project_dir))
    output_dir = os.path.join(project_dir, 'output')
    config_file = os.path.join(project_dir, 'config.json')

    with open(config_file, 'r') as handle:
        config = json.load(handle)
    model_config = config['model']
    output_path = os.path.join(
        output_dir, model_config.get('inp_name', DEFAULT_OUTPUT_NAME))

    meta = read_meta(os.path.join(output_dir, 'meta.csv'))
    grains = read_grain_props(os.path.join(output_dir, 'grains.csv'))
    grid = read_grid(os.path.join(output_dir, 'map.csv'))

    nx, ny = build_inp(
        output_path=output_path,
        meta=meta,
        grid=grid,
        grains=grains,
        element_type=model_config['element_type'],
        depvar_count=int(model_config['depvar_count']),
        umat_prefix=[float(value) for value in model_config['umat_prefix']],
        umat_suffix=[float(value) for value in model_config['umat_suffix']])

    print('Wrote %s' % output_path)
    print('Elements: %d' % (nx * ny))
    print('Nodes: %d' % ((nx + 1) * (ny + 1)))
    print('Grains/materials: %d' % len(grains))


if __name__ == '__main__':
    main()
