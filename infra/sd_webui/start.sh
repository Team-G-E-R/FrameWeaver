#!/bin/sh
set -e

cd /opt/sd_webui

export PYTHONUNBUFFERED=1
export CUDA_VISIBLE_DEVICES=""
export TORCH_COMMAND="pip install torch==2.1.2+cpu torchvision==0.16.2+cpu --index-url https://download.pytorch.org/whl/cpu"

# 1) убираем hash-проверки (иначе ловишь mismatch как с opencv-python)
if [ -f "/opt/sd_webui/requirements_versions.txt" ]; then
  sed -i 's/ --hash=sha256:[0-9a-f]\{64\}//g' /opt/sd_webui/requirements_versions.txt
fi

# 2) гарантируем наличие taming-transformers как репозитория и ставим editable
mkdir -p /opt/sd_webui/repositories
if [ ! -d "/opt/sd_webui/repositories/taming-transformers/.git" ]; then
  git clone https://github.com/CompVis/taming-transformers.git /opt/sd_webui/repositories/taming-transformers
fi

python -m pip install --no-cache-dir einops
python -m pip install --no-cache-dir -e /opt/sd_webui/repositories/taming-transformers

# 3) жёсткая проверка, что нужный импорт реально работает
python - << 'PY'
import taming
from taming.modules.vqvae.quantize import VectorQuantizer2
import taming.modules.vqvae.quantize as q
print("taming ok:", getattr(taming, "__path__", None))
print("quantize ok:", q.__file__)
PY

# 3) midas stub (если в stable-diffusion-stability-ai нет ldm/modules/midas, WebUI падает на импорте)
MIDAS_DIR="/opt/sd_webui/repositories/stable-diffusion-stability-ai/ldm/modules/midas"

if [ ! -d "$MIDAS_DIR" ]; then
  mkdir -p "$MIDAS_DIR"

  cat > "$MIDAS_DIR/__init__.py" <<'PY'
from . import api  # noqa: F401
PY

  cat > "$MIDAS_DIR/api.py" <<'PY'
def load_model(*args, **kwargs):
    raise RuntimeError("MiDaS (depth) module is not included in this CPU MVP build.")
PY
fi

# 4) стартуем WebUI
python launch.py \
  --listen --port 7860 \
  --api \
  --use-cpu all \
  --skip-torch-cuda-test