#!/bin/bash
# Build the lumina_io C++ core extension.
# Usage:  ./build.sh        (run inside the conda env you'll use the package from)
#
# HDF5 is located in this order (a serial build is recommended -- the core
# never calls MPI, its parallelism is thread-based):
#   1. $HDF5_PREFIX, if set
#   2. $CONDA_PREFIX  (conda-forge: `conda install hdf5`; serial, shared lib)
#   3. the Engaging `hdf5/1.14.3` module (a parallel build; its MPI support
#      libraries are added to the link line automatically)
set -e
cd "$(dirname "$0")"

has_hdf5() { [ -n "$1" ] && { [ -f "$1/lib/libhdf5.a" ] || [ -f "$1/lib/libhdf5.so" ]; }; }

if ! has_hdf5 "$HDF5_PREFIX"; then
    if has_hdf5 "$CONDA_PREFIX"; then
        HDF5_PREFIX=$CONDA_PREFIX
    else
        echo "No HDF5 found via HDF5_PREFIX or CONDA_PREFIX;" \
             "trying 'module load community-modules hdf5/1.14.3'" >&2
        module load community-modules hdf5/1.14.3
        HDF5_PREFIX=$(dirname "$(dirname "$(which h5dump)")")
    fi
fi
echo "Using HDF5 from ${HDF5_PREFIX}"

# Prefer static linking when libhdf5.a exists; otherwise link the shared
# library with an rpath so the extension finds it at import time.
if [ -f "${HDF5_PREFIX}/lib/libhdf5.a" ]; then
    # zlib satisfies the static lib's deflate filter (unneeded when linking
    # libhdf5.so, which carries its own dependencies). -l:libz.so.1 links the
    # runtime library directly, since conda envs lack the libz.so dev symlink.
    HDF5_LINK="${HDF5_PREFIX}/lib/libhdf5.a -l:libz.so.1"
    # A static libhdf5 needs its support libs too (a parallel build lists its
    # MPI library here): "Extra libraries: m;dl;/path/to/libmpi.so"
    for lib in $(sed -n 's/^ *Extra libraries: *//p' \
                     "${HDF5_PREFIX}/lib/libhdf5.settings" 2>/dev/null | tr ';' ' '); do
        case "$lib" in
            /*) HDF5_LINK="$HDF5_LINK $lib -Wl,-rpath,$(dirname "$lib")" ;;
            *)  HDF5_LINK="$HDF5_LINK -l$lib" ;;
        esac
    done
else
    HDF5_LINK="-L${HDF5_PREFIX}/lib -lhdf5 -Wl,-rpath,${HDF5_PREFIX}/lib"
fi

PYBIND_INC=$(python3 -m pybind11 --includes)
EXT_SUFFIX=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX'))")
OUT=lumina_io/_core${EXT_SUFFIX}

set -x
g++ -O3 -std=c++17 -shared -fPIC -fvisibility=hidden -pthread \
    ${PYBIND_INC} -I"${HDF5_PREFIX}/include" \
    src/lumina_core.cpp \
    ${HDF5_LINK} \
    -lm -ldl -o "${OUT}"
set +x
echo "Built ${OUT}"
