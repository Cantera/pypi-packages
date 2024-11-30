#!/bin/bash
# Copied from h5py. Licensed under the BSD 3-Clause license.
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

if [[ "$1" == "" ]] ; then
    echo "Usage: $0 <PROJECT_PATH>"
    exit 1
fi
PROJECT_PATH="$1"

# HDF5
HDF5_VERSION="1.14.5"
ZLIB_VERSION="1.3.1"
LIBAEC_VERSION="1.1.3"
HIGHFIVE_VERSION="2.10.0"

HDF5_DIR="${PROJECT_PATH}/cache/hdf5/${HDF5_VERSION}"
HIGHFIVE_DIR="${PROJECT_PATH}/cache/highfive/${HIGHFIVE_VERSION}"

pushd ${RUNNER_TEMP}

set +x

curl -fsSLO "https://github.com/HDFGroup/hdf5/releases/download/hdf5_${HDF5_VERSION}/hdf5-${HDF5_VERSION}.tar.gz"
tar -xzvf hdf5-${HDF5_VERSION}.tar.gz
mkdir -p hdf5-${HDF5_VERSION}/build
pushd hdf5-${HDF5_VERSION}/build

cmake -G "Visual Studio 17 2022" \
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

cmake --build . --target install --config Release
popd

curl -fsSLO https://github.com/BlueBrain/HighFive/archive/refs/tags/v${HIGHFIVE_VERSION}.tar.gz
tar -xzf v${HIGHFIVE_VERSION}.tar.gz
mkdir -p HighFive-${HIGHFIVE_VERSION}/build
pushd HighFive-${HIGHFIVE_VERSION}/build

cmake -G "Visual Studio 17 2022" \
    -DCMAKE_BUILD_TYPE=Release \
    -DHDF5_ROOT="${HDF5_DIR}" \
    -DCMAKE_INSTALL_PREFIX="${HIGHFIVE_DIR}" \
    -DHIGHFIVE_USE_BOOST:BOOL=OFF \
    -DHIGHFIVE_UNIT_TESTS:BOOL=OFF \
    -DHIGHFIVE_EXAMPLES:BOOL=OFF \
    -DHIGHFIVE_BUILD_DOCS:BOOL=OFF \
    ..

cmake --build . --target install --config Release
popd

find $HDF5_DIR -type f
find $HIGHFIVE_DIR -type f

if [[ "$GITHUB_ENV" != "" ]] ; then
    # PATH on windows is special
    echo "$EXTRA_PATH" | tee -a $GITHUB_PATH
    echo "CL=$CL" | tee -a $GITHUB_ENV
    echo "LINK=$LINK" | tee -a $GITHUB_ENV
    echo "HDF5_ROOT=$HDF5_DIR" | tee -a $GITHUB_ENV
    echo "HighFive_ROOT=$HIGHFIVE_DIR" | tee -a $GITHUB_ENV
fi

set -x
