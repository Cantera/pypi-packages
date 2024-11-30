#!/bin/bash
# Adapted from h5py. Licensed under the BSD 3-Clause license.
# Copyright (c) 2008 Andrew Collette and contributors
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

set -eo pipefail

function setup_github_env {
    if [[ "$GITHUB_ENV" != "" ]]; then
        echo "HDF5_ROOT=${HDF5_DIR}" | tee -a $GITHUB_ENV
        echo "HighFive_ROOT=${HIGHFIVE_DIR}" | tee -a $GITHUB_ENV
        echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}" | tee -a $GITHUB_ENV
        echo "MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET}" | tee -a $GITHUB_ENV
        echo "DYLD_FALLBACK_LIBRARY_PATH=${HDF5_DIR}/lib" | tee -a $GITHUB_ENV
    fi
}

set +x

if [[ "$1" == "" ]] ; then
    echo "Usage: $0 <PROJECT_PATH>"
    exit 1
fi
PROJECT_PATH="$1"
ARCH=$(uname -m)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

source "${SCRIPT_DIR}/dependencies.sh"

HDF5_DIR="${PROJECT_PATH}/cache/hdf5/${HDF5_VERSION}-${ARCH}"
HIGHFIVE_DIR="${PROJECT_PATH}/cache/highfive/${HIGHFIVE_VERSION}-${ARCH}"

# When compiling HDF5, we should use the minimum across all Python versions for a given
# arch, for versions see for example a more updated version of the following:
# https://github.com/pypa/cibuildwheel/blob/9c75ea15c2f31a77e6043b80b1b7081372319d85/cibuildwheel/macos.py#L302-L315
if [[ "${ARCH}" == "arm64" ]]; then
    export MACOSX_DEPLOYMENT_TARGET="11.0"
else
    # This is the minimum version for Cantera
    export MACOSX_DEPLOYMENT_TARGET="10.15"
fi

lib_name=libhdf5.dylib
inc_name=highfive.hpp

if [ -f ${HDF5_DIR}/lib/${lib_name} ] && [ -f ${HIGHFIVE_DIR}/include/highfive/${inc_name} ]; then
    echo "using cached build"
    setup_github_env
    exit 0
else
    echo "building HDF5"
fi

brew install ninja cmake

pushd ${RUNNER_TEMP}

curl -fsSLO "https://github.com/HDFGroup/hdf5/releases/download/hdf5_${HDF5_VERSION}/hdf5-${HDF5_VERSION}.tar.gz"
tar -xzf hdf5-${HDF5_VERSION}.tar.gz
mkdir -p hdf5-${HDF5_VERSION}/build
pushd hdf5-${HDF5_VERSION}/build

cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="${HDF5_DIR}" \
    -DHDF5_ENABLE_Z_LIB_SUPPORT:BOOL=ON \
    -DHDF5_ENABLE_SZIP_SUPPORT:BOOL=ON \
    -DHDF5_BUILD_EXAMPLES:BOOL=OFF \
    -DHDF5_BUILD_TOOLS:BOOL=OFF \
    -DBUILD_TESTING:BOOL=OFF \
    -DHDF5_ALLOW_EXTERNAL_SUPPORT:STRING=TGZ \
    -DZLIB_PACKAGE_NAME:STRING=zlib \
    -DZLIB_TGZ_NAME:STRING=zlib-${ZLIB_VERSION}.tar.gz \
    -DZLIB_TGZ_ORIGPATH:STRING=https://github.com/madler/zlib/releases/download/v${ZLIB_VERSION} \
    -DZLIB_USE_LOCALCONTENT:BOOL=OFF \
    -DLIBAEC_PACKAGE_NAME:STRING=libaec \
    -DLIBAEC_TGZ_NAME:STRING=libaec-${LIBAEC_VERSION}.tar.gz \
    -DLIBAEC_TGZ_ORIGPATH:STRING=https://github.com/MathisRosenhauer/libaec/releases/download/v${LIBAEC_VERSION} \
    -DLIBAEC_USE_LOCALCONTENT:BOOL=OFF \
    -DHDF_PACKAGE_NAMESPACE:STRING=ct_ \
    ..

ninja install
popd

curl -fsSLO https://github.com/BlueBrain/HighFive/archive/refs/tags/v${HIGHFIVE_VERSION}.tar.gz
tar -xzf v${HIGHFIVE_VERSION}.tar.gz
mkdir -p HighFive-${HIGHFIVE_VERSION}/build
pushd HighFive-${HIGHFIVE_VERSION}/build

cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DHDF5_ROOT="${HDF5_DIR}" \
    -DCMAKE_INSTALL_PREFIX="${HIGHFIVE_DIR}" \
    -DHIGHFIVE_USE_BOOST:BOOL=OFF \
    -DHIGHFIVE_UNIT_TESTS:BOOL=OFF \
    -DHIGHFIVE_EXAMPLES:BOOL=OFF \
    -DHIGHFIVE_BUILD_DOCS:BOOL=OFF \
    ..

ninja install
popd

setup_github_env

set -x
