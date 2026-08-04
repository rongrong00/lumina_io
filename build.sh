#!/bin/bash
# Build the lumina_io C++ core extension (statically linked against HDF5).
# Usage:  ./build.sh        (run inside the conda env you'll use the package from)
set -e
cd "$(dirname "$0")"

HDF5_PREFIX=${HDF5_PREFIX:-}
if [ -z "$HDF5_PREFIX" ] || [ ! -f "$HDF5_PREFIX/lib/libhdf5.a" ]; then
    echo "libhdf5.a not found at HDF5_PREFIX; trying 'module load hdf5'" >&2
    module load hdf5/1.12.1
    HDF5_PREFIX=$(dirname "$(dirname "$(which h5dump)")")
fi

PYBIND_INC=$(python3 -m pybind11 --includes)
EXT_SUFFIX=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")
OUT=lumina_io/_core${EXT_SUFFIX}

set -x
g++ -O3 -std=c++17 -shared -fPIC -fvisibility=hidden -pthread \
    ${PYBIND_INC} -I"${HDF5_PREFIX}/include" \
    src/lumina_core.cpp \
    "${HDF5_PREFIX}/lib/libhdf5.a" \
    -lz -lm -ldl -o "${OUT}"
set +x
echo "Built ${OUT}"
