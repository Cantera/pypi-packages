#!/bin/bash

function strip_components() {
    local tar_file=$1
    if tar tf "${tar_file}" | head -n 1 | grep -q '^./$'; then STRIP_COMPONENTS_COUNT=2; else STRIP_COMPONENTS_COUNT=1; fi;
    printf '%s\n' $STRIP_COMPONENTS_COUNT;
}

function hdf5() {
    local tar_file="hdf5-${HDF5_VERSION}.tar.gz"
    curl -fsSLO "https://github.com/HDFGroup/hdf5/releases/download/hdf5_${HDF5_VERSION}/${tar_file}"
    mkdir -p "hdf5-${HDF5_VERSION}/build"
    tar -xzf "${tar_file}" --strip-components="$(strip_components "$tar_file")" -C "hdf5-${HDF5_VERSION}"
    pushd "hdf5-${HDF5_VERSION}/build" || exit

    cmake -G "$GENERATOR" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${HDF5_DIR}" \
        -DHDF5_ENABLE_Z_LIB_SUPPORT:BOOL=ON \
        -DHDF5_ENABLE_SZIP_SUPPORT:BOOL=ON \
        -DHDF5_BUILD_EXAMPLES:BOOL=OFF \
        -DHDF5_BUILD_TOOLS:BOOL=OFF \
        -DBUILD_TESTING:BOOL=OFF \
        -DHDF5_ALLOW_EXTERNAL_SUPPORT:STRING=TGZ \
        -DZLIB_PACKAGE_NAME:STRING=zlib \
        -DZLIB_TGZ_NAME:STRING="zlib-${ZLIB_VERSION}.tar.gz" \
        -DZLIB_TGZ_ORIGPATH:STRING="https://github.com/madler/zlib/releases/download/v${ZLIB_VERSION}" \
        -DZLIB_USE_LOCALCONTENT:BOOL=OFF \
        -DLIBAEC_PACKAGE_NAME:STRING=libaec \
        -DLIBAEC_TGZ_NAME:STRING="libaec-${LIBAEC_VERSION}.tar.gz" \
        -DLIBAEC_TGZ_ORIGPATH:STRING="https://github.com/MathisRosenhauer/libaec/releases/download/v${LIBAEC_VERSION}" \
        -DLIBAEC_USE_LOCALCONTENT:BOOL=OFF \
        -DHDF_PACKAGE_NAMESPACE:STRING=ct_ \
        ..

    cmake --build . --target install --config Release
    popd || exit
}

function highfive() {
    local tar_file="v${HIGHFIVE_VERSION}.tar.gz"
    curl -fsSLO "https://github.com/highfive-devs/highfive/archive/refs/tags/${tar_file}"
    mkdir -p "highfive-v${HIGHFIVE_VERSION}/build"
    tar -xvzf "${tar_file}" --strip-components="$(strip_components "$tar_file")" -C "highfive-v${HIGHFIVE_VERSION}"
    pushd "highfive-v${HIGHFIVE_VERSION}/build" || exit

    cmake -G "$GENERATOR" \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_BUILD_TYPE=Release \
        -DHDF5_ROOT="${HDF5_DIR}" \
        -DCMAKE_INSTALL_PREFIX="${HIGHFIVE_DIR}" \
        -DHIGHFIVE_USE_BOOST:BOOL=OFF \
        -DHIGHFIVE_UNIT_TESTS:BOOL=OFF \
        -DHIGHFIVE_EXAMPLES:BOOL=OFF \
        -DHIGHFIVE_BUILD_DOCS:BOOL=OFF \
        ..

    cmake --build . --target install --config Release
    popd || exit
}

function sundials() {
    local tar_file="sundials-${SUNDIALS_VERSION}.tar.gz"
    curl -fsSLO "https://github.com/LLNL/sundials/releases/download/v${SUNDIALS_VERSION}/${tar_file}"
    mkdir -p "sundials-${SUNDIALS_VERSION}/build"
    tar -xzf "$tar_file" --strip-components="$(strip_components "$tar_file")" -C "sundials-${SUNDIALS_VERSION}"
    pushd "sundials-${SUNDIALS_VERSION}/build" || exit

    cmake -G "$GENERATOR" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${SUNDIALS_DIR}" \
        -DEXAMPLES_INSTALL=OFF \
        -DEXAMPLES_ENABLE_C=OFF \
        -DBUILD_ARKODE=OFF \
        -DBUILD_CVODE=OFF \
        -DBUILD_IDA=OFF \
        -DBUILD_KINSOL=OFF \
        -DBUILD_CPODES=OFF \
        -DBUILD_FORTRAN_MODULE_INTERFACE=OFF \
        "${SUNDIALS_BUILD_OPTIONS[@]}" \
        ..

    cmake --build . --target install --config Release
    popd || exit
}

function yaml_cpp() {
    local tar_file="${YAML_CPP_VERSION}.tar.gz"
    curl -fsSLO "https://github.com/jbeder/yaml-cpp/archive/refs/tags/${tar_file}"
    mkdir -p "yaml-cpp-${YAML_CPP_VERSION}/build"
    tar -xzf "$tar_file" --strip-components="$(strip_components "$tar_file")" -C "yaml-cpp-${YAML_CPP_VERSION}"
    pushd "yaml-cpp-${YAML_CPP_VERSION}/build" || exit

    cmake -G "$GENERATOR" \
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DCMAKE_INSTALL_PREFIX="${YAML_CPP_DIR}" \
        -DCMAKE_BUILD_TYPE:STRING=Release \
        -DCMAKE_INSTALL_LIBDIR:STRING=lib \
        -DYAML_CPP_FORMAT_SOURCE:BOOL=OFF \
        -DBUILD_TESTING:BOOL=OFF \
        -DBUILD_SHARED_LIBS:BOOL=ON \
        ..

    cmake --build . --target install --config Release
    popd || exit
}

function main() {
    pushd "${RUNNER_TEMP}" || exit
    hdf5
    highfive
    sundials
    yaml_cpp
}
