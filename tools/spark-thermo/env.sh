# Copy to $THERMO_BASE/env.sh on the remote machine. Keeps every cache and temp file inside the work directory,
# so that deleting it removes everything (nothing in the owner's ~/.cache, ~/.config or /tmp).
B=${THERMO_BASE:-$HOME/thermo-work}
export THERMO_BASE=$B
export PATH=$B/venv/bin:$HOME/.local/bin:$PATH
export UV_CACHE_DIR=$B/cache/uv UV_PYTHON_INSTALL_DIR=$B/cache/uv-python UV_TOOL_DIR=$B/cache/uv-tools UV_PYTHON_BIN_DIR=$B/cache/uv-bin
export TORCH_HOME=$B/cache/torch HF_HOME=$B/cache/hf XDG_CACHE_HOME=$B/cache/xdg XDG_CONFIG_HOME=$B/cache/config MPLCONFIGDIR=$B/cache/mpl
export CUDA_CACHE_PATH=$B/cache/nv TRITON_CACHE_DIR=$B/cache/triton PYTORCH_KERNEL_CACHE_PATH=$B/cache/torch-kernels
export TORCHINDUCTOR_CACHE_DIR=$B/cache/inductor PIP_CACHE_DIR=$B/cache/pip PYTHONPYCACHEPREFIX=$B/cache/pycache
export TMPDIR=$B/tmp
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 OPENCV_NUM_THREADS=4
export HISTFILE=/dev/null
export GOV_DUTY=${GOV_DUTY:-0.5}
export PYTHONPATH=$B/code${PYTHONPATH:+:$PYTHONPATH}
mkdir -p $TMPDIR
