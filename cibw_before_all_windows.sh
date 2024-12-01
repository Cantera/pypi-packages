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
set +x

function setup_github_env {
    echo "HDF5_ROOT=$HDF5_DIR" | tee -a $GITHUB_ENV
    echo "HDF5_LIB_DIR=$HDF5_DIR\bin" | tee -a $GITHUB_ENV
    echo "HighFive_ROOT=$HIGHFIVE_DIR" | tee -a $GITHUB_ENV
}

if [[ "$1" == "" ]] ; then
    echo "Usage: $0 <PROJECT_PATH>"
    exit 1
fi
PROJECT_PATH="$1"

GENERATOR="Visual Studio 17 2022"
SCRIPT_DIR=$( cd -P "$( dirname "$(readlink -f "$0")" )" && pwd )

HDF5_DIR="${PROJECT_PATH}/cache/hdf5/${HDF5_VERSION}"
HIGHFIVE_DIR="${PROJECT_PATH}/cache/highfive/${HIGHFIVE_VERSION}"

lib_name=hdf5.dll
inc_name=highfive.hpp

if [ -f ${HDF5_DIR}/bin/${lib_name} ] && [ -f ${HIGHFIVE_DIR}/include/highfive/${inc_name} ]; then
    echo "using cached build"
    setup_github_env
    exit 0
else
    echo "building HDF5"
fi

source "${SCRIPT_DIR}/dependencies.sh"
source "${SCRIPT_IDR}/build_dependencies.sh"

setup_github_env
