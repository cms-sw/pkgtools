export CMAKE_BUILD_PARALLEL_LEVEL="$1"
export MAX_JOBS="$1"
export CMS_NINJA_NUM_JOBS="$1"
export CYTHON_NTHREADS="$1"
export MESON_NUM_PROCESSES="$1"

#Env variables OMP_* are to limit the rpmdeps (which is run during rpmbuild packaging stage)
export OMP_NUM_THREADS="$1"
export OMP_THREAD_LIMIT="$1"
export OMP_DYNAMIC=FALSE

# To limit the parallel process run by cargo
export CARGO_BUILD_JOBS="$1"
export CARGO_HOME="${TMPDIR}/cargo_home"
