% Rebuild a real EBSD voxel model from Oxford CTF/CRC data with MTEX.
%
% Project settings are read from ../config.json.
% Outputs are written to ../output:
%   grains.csv      one row per retained alpha grain
%   map.csv         ny-by-nx grain id map, one EBSD pixel per element
%   meta.csv        grid dimensions, spacing, and model scale
%   mtex.png        direct MTEX IPF plot
%   abq.png         voxel IPF plot exactly matching the Abaqus element map

clear;
clc;
warning('off', 'MATLAB:ui:Figure:a11yTextScalingNotSupported');

SCRIPT_DIR = fileparts(mfilename('fullpath'));
if isempty(SCRIPT_DIR)
    SCRIPT_DIR = pwd;
end
ROOT_DIR = getenv('EBSD2ABAQUS_PROJECT');
if isempty(ROOT_DIR)
    ROOT_DIR = fileparts(SCRIPT_DIR);
end

CONFIG_FILE = fullfile(ROOT_DIR, 'config.json');
if ~exist(CONFIG_FILE, 'file')
    error('Cannot find project configuration: %s', CONFIG_FILE);
end
cfg = jsondecode(fileread(CONFIG_FILE));

INPUT_FILE = fullfile(ROOT_DIR, strrep(cfg.input_file, '/', filesep));
OUT_DIR = fullfile(ROOT_DIR, 'output');

PRIMARY_PHASE = cfg.primary_phase.name;
MISORIENTATION_DEG = cfg.grain_reconstruction.misorientation_deg;
MIN_GRAIN_PIXELS = cfg.grain_reconstruction.min_grain_pixels;

% EBSD is in micrometre. Abaqus model coordinates are written in mm.
MODEL_SCALE = cfg.model.coordinate_scale;

COORDINATE_MODE = 'original_mtex_view';

if ~exist(INPUT_FILE, 'file')
    error('Cannot find EBSD input file: %s', INPUT_FILE);
end
if ~exist(OUT_DIR, 'dir')
    mkdir(OUT_DIR);
end

CS = { ...
    'notIndexed', ...
    crystalSymmetry(cfg.primary_phase.symmetry, ...
        cfg.primary_phase.lattice_parameters(:).', ...
        'X||a*', 'Y||b', 'Z||c', 'mineral', cfg.primary_phase.name), ...
    crystalSymmetry(cfg.secondary_phase.symmetry, ...
        cfg.secondary_phase.lattice_parameters(:).', ...
        'mineral', cfg.secondary_phase.name) ...
};

fprintf('Loading EBSD: %s\n', INPUT_FILE);
ebsd = EBSD.load(INPUT_FILE, CS, 'interface', 'ctf', ...
    'convertEuler2SpatialReferenceFrame');

fprintf('Mineral list:\n');
disp(ebsd.mineralList');
for k = 1:numel(ebsd.mineralList)
    fprintf('  %s: %d points\n', ebsd.mineralList{k}, length(ebsd(ebsd.mineralList{k})));
end

alpha = ebsd(PRIMARY_PHASE);
if isempty(alpha)
    error('Primary phase "%s" has no EBSD points.', PRIMARY_PHASE);
end

fprintf('Reconstructing grains: angle %.3g deg, min %d pixels\n', ...
    MISORIENTATION_DEG, MIN_GRAIN_PIXELS);
[grainsAll, alpha.grainId] = calcGrains(alpha, ...
    'angle', MISORIENTATION_DEG * degree);

grains = grainsAll(grainsAll.grainSize >= MIN_GRAIN_PIXELS);
if isempty(grains)
    error('No grains remain after MIN_GRAIN_PIXELS filtering.');
end

sourceIds = grains.id(:);
validAlpha = ismember(alpha.grainId, sourceIds);
[~, seqIdsForAlpha] = ismember(alpha.grainId(validAlpha), sourceIds);

fprintf('Retained alpha grains: %d\n', length(grains));
fprintf('Valid alpha pixels used for nearest fill: %d / %d\n', ...
    nnz(validAlpha), length(alpha));

F = scatteredInterpolant( ...
    double(alpha.x(validAlpha)), ...
    double(alpha.y(validAlpha)), ...
    double(seqIdsForAlpha), ...
    'nearest', 'nearest');

grainIdAll = round(F(double(ebsd.x(:)), double(ebsd.y(:))));
if any(isnan(grainIdAll)) || any(grainIdAll < 1)
    error('Nearest-grain fill failed for some EBSD pixels.');
end

coordTol = 1.0e-7;
x = double(ebsd.x(:));
y = double(ebsd.y(:));
xKey = round(x / coordTol) * coordTol;
yKey = round(y / coordTol) * coordTol;
xVals = unique(xKey);
yVals = unique(yKey);
nx = numel(xVals);
ny = numel(yVals);

if nx * ny ~= length(ebsd)
    error('EBSD data is not a complete regular grid: nx*ny=%d, points=%d.', ...
        nx * ny, length(ebsd));
end

dx = median(diff(xVals));
dy = median(diff(yVals));
if ~(dx > 0) || ~(dy > 0)
    error('Invalid EBSD grid spacing dx=%g dy=%g.', dx, dy);
end

col = round((xKey - xVals(1)) / dx) + 1;
row = round((yKey - yVals(1)) / dy) + 1;
if any(row < 1 | row > ny | col < 1 | col > nx)
    error('Computed grid indices out of range.');
end

grainGrid = zeros(ny, nx);
gridIndex = sub2ind([ny, nx], row, col);
grainGrid(gridIndex) = grainIdAll;
if any(grainGrid(:) == 0)
    error('Some grid cells were not assigned a grain id.');
end

[phi1, Phi, phi2] = Euler(grains.meanOrientation);
grainSizePixels = double(grains.grainSize(:));
areaUm2 = grainSizePixels * dx * dy;
equivDiameterUm = 2.0 * sqrt(areaUm2 / pi);

grainTable = table( ...
    (1:length(grains)).', ...
    sourceIds, ...
    repmat({PRIMARY_PHASE}, length(grains), 1), ...
    phi1(:) / degree, ...
    Phi(:) / degree, ...
    phi2(:) / degree, ...
    grainSizePixels, ...
    areaUm2, ...
    equivDiameterUm, ...
    equivDiameterUm * MODEL_SCALE, ...
    'VariableNames', { ...
        'GrainID', 'SourceGrainID', 'Phase', ...
        'phi1', 'Phi', 'phi2', ...
        'GrainSizePixels', 'Area_um2', ...
        'EquivalentDiameter_um', 'EquivalentDiameter_model' ...
    });

writetable(grainTable, fullfile(OUT_DIR, 'grains.csv'));
writematrix(grainGrid, fullfile(OUT_DIR, 'map.csv'));

fid = fopen(fullfile(OUT_DIR, 'meta.csv'), 'w');
fprintf(fid, 'key,value\n');
fprintf(fid, 'source_file,%s\n', INPUT_FILE);
fprintf(fid, 'primary_phase,%s\n', PRIMARY_PHASE);
fprintf(fid, 'misorientation_deg,%.12g\n', MISORIENTATION_DEG);
fprintf(fid, 'min_grain_pixels,%d\n', MIN_GRAIN_PIXELS);
fprintf(fid, 'nx,%d\n', nx);
fprintf(fid, 'ny,%d\n', ny);
fprintf(fid, 'x_min_um,%.12g\n', xVals(1));
fprintf(fid, 'x_max_um,%.12g\n', xVals(end));
fprintf(fid, 'y_min_um,%.12g\n', yVals(1));
fprintf(fid, 'y_max_um,%.12g\n', yVals(end));
fprintf(fid, 'dx_um,%.12g\n', dx);
fprintf(fid, 'dy_um,%.12g\n', dy);
fprintf(fid, 'model_scale,%.12g\n', MODEL_SCALE);
fprintf(fid, 'coordinate_mode,%s\n', COORDINATE_MODE);
fprintf(fid, 'retained_grains,%d\n', length(grains));
fprintf(fid, 'total_pixels,%d\n', numel(grainGrid));
fclose(fid);

try
    fig = figure('Visible', 'off');
    plot(alpha, alpha.orientations);
    hold on;
    plot(grains.boundary, 'lineColor', 'k', 'lineWidth', 0.5);
    if exist('axtoolbar', 'file')
        axtoolbar(gca, {});
    end
    title('MTEX direct IPF map');
    exportgraphics(fig, fullfile(OUT_DIR, 'mtex.png'), 'Resolution', 200);
    close(fig);

    try
        ipfKey = ipfColorKey(grains.CS);
        grainColors = ipfKey.orientation2color(grains.meanOrientation);
    catch
        grainColors = hsv(length(grains));
    end

    rgb = zeros(ny, nx, 3);
    for gid = 1:length(grains)
        mask = grainGrid == gid;
        for channelId = 1:3
            channel = rgb(:, :, channelId);
            channel(mask) = grainColors(gid, channelId);
            rgb(:, :, channelId) = channel;
        end
    end

    edgeMask = false(ny, nx);
    edgeMask(:, 2:end) = edgeMask(:, 2:end) | grainGrid(:, 2:end) ~= grainGrid(:, 1:end-1);
    edgeMask(2:end, :) = edgeMask(2:end, :) | grainGrid(2:end, :) ~= grainGrid(1:end-1, :);

    fig = figure('Visible', 'off');
    image([0, (nx - 1) * dx], [0, (ny - 1) * dy], rgb);
    hold on;
    contour((0:nx-1) * dx, (0:ny-1) * dy, double(edgeMask), [1 1], 'k', 'LineWidth', 0.5);
    axis image;
    set(gca, 'YDir', 'normal');
    if exist('axtoolbar', 'file')
        axtoolbar(gca, {});
    end
    title('Abaqus voxel IPF map');
    xlabel('x (um)');
    ylabel('y (um)');
    exportgraphics(fig, fullfile(OUT_DIR, 'abq.png'), 'Resolution', 200);
    close(fig);
catch ME
    warning('Plot export skipped: %s', ME.message);
end

fprintf('Done.\n');
fprintf('  %s\n', fullfile(OUT_DIR, 'grains.csv'));
fprintf('  %s\n', fullfile(OUT_DIR, 'map.csv'));
fprintf('  %s\n', fullfile(OUT_DIR, 'meta.csv'));
