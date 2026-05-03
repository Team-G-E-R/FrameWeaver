import base64
import os
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
from audiocraft.models import AudioGen, MAGNeT, MusicGen
from scipy.io import wavfile

from app.schemas import GenerateSoundRequest, GenerateSoundResponse


@dataclass(frozen=True)
class SoundGenerationConfig:
    model_name: str
    device: str
    default_duration_seconds: float
    max_duration_seconds: float
    top_k: int
    top_p: float
    temperature: float
    cfg_coef: float
    min_cfg_coef: float
    max_cfg_coef: float


class SoundGenerator:
    def __init__(self) -> None:
        self.config = SoundGenerationConfig(
            model_name=os.getenv("SOUND_GENERATION_MODEL_NAME", "facebook/musicgen-small"),
            device=os.getenv("SOUND_GENERATION_DEVICE", "cpu"),
            default_duration_seconds=float(os.getenv("SOUND_GENERATION_DEFAULT_DURATION_SECONDS", "5")),
            max_duration_seconds=float(os.getenv("SOUND_GENERATION_MAX_DURATION_SECONDS", "15")),
            top_k=int(os.getenv("SOUND_GENERATION_TOP_K", "250")),
            top_p=float(os.getenv("SOUND_GENERATION_TOP_P", "0.0")),
            temperature=float(os.getenv("SOUND_GENERATION_TEMPERATURE", "1.0")),
            cfg_coef=float(os.getenv("SOUND_GENERATION_CFG_COEF", "3.0")),
            min_cfg_coef=float(os.getenv("SOUND_GENERATION_MIN_CFG_COEF", "1.0")),
            max_cfg_coef=float(os.getenv("SOUND_GENERATION_MAX_CFG_COEF", "3.0")),
        )

        self.model = self._load_model()
        self._disable_memory_efficient_attention_for_cpu()

    def generate(self, request: GenerateSoundRequest) -> GenerateSoundResponse:
        started_at = time.perf_counter()

        duration_seconds = self._clamp_duration(request.duration_seconds)
        prompt = self._prepare_prompt(request.prompt)

        self._set_generation_params(duration_seconds)

        print(
            f"Sound generation started: model={self.config.model_name}, "
            f"device={self.config.device}, duration={duration_seconds}, prompt={prompt!r}",
            flush=True,
        )

        with torch.inference_mode():
            wav = self.model.generate([prompt])

        sample_rate = int(self.model.sample_rate)
        wav_tensor = wav[0].detach().cpu()
        wav_tensor = self._trim_wav_tensor(wav_tensor, sample_rate, duration_seconds)

        wav_bytes = self._tensor_to_wav_bytes(wav_tensor, sample_rate)
        audio_base64 = base64.b64encode(wav_bytes).decode("ascii")

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        return GenerateSoundResponse(
            audio_base64=audio_base64,
            model=self.config.model_name,
            prompt=prompt,
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            duration_ms=duration_ms,
        )

    def _load_model(self):
        if self._is_magnet_model():
            return MAGNeT.get_pretrained(self.config.model_name, device=self.config.device)

        if self._is_musicgen_model():
            return MusicGen.get_pretrained(self.config.model_name, device=self.config.device)

        return AudioGen.get_pretrained(self.config.model_name, device=self.config.device)

    def _set_generation_params(self, duration_seconds: float) -> None:
        if self._is_magnet_model():
            self.model.set_generation_params(
                top_k=self.config.top_k,
                top_p=self.config.top_p,
                temperature=self.config.temperature,
                min_cfg_coef=self.config.min_cfg_coef,
                max_cfg_coef=self.config.max_cfg_coef,
            )
            return

        self.model.set_generation_params(
            duration=duration_seconds,
            top_k=self.config.top_k,
            top_p=self.config.top_p,
            temperature=self.config.temperature,
            cfg_coef=self.config.cfg_coef,
        )

    def _disable_memory_efficient_attention_for_cpu(self) -> None:
        if self.config.device.lower() != "cpu":
            return

        changed = 0

        for root in self._iter_torch_module_roots():
            for module in root.modules():
                if hasattr(module, "memory_efficient"):
                    try:
                        setattr(module, "memory_efficient", False)
                        changed += 1
                    except Exception:
                        pass

        print(f"Disabled memory_efficient attention for CPU modules: {changed}", flush=True)

    def _iter_torch_module_roots(self) -> Iterable[nn.Module]:
        seen: set[int] = set()

        def emit(value: object) -> Iterable[nn.Module]:
            if not isinstance(value, nn.Module):
                return

            obj_id = id(value)
            if obj_id in seen:
                return

            seen.add(obj_id)
            yield value

        yield from emit(self.model)

        for attr_name in (
            "lm",
            "compression_model",
            "condition_provider",
            "watermarking_model",
            "model",
            "transformer",
        ):
            yield from emit(getattr(self.model, attr_name, None))

        for value in getattr(self.model, "__dict__", {}).values():
            yield from emit(value)

    def _is_magnet_model(self) -> bool:
        return "magnet" in self.config.model_name.lower()

    def _is_musicgen_model(self) -> bool:
        return "musicgen" in self.config.model_name.lower()

    def _clamp_duration(self, value: float | None) -> float:
        if value is None:
            value = self.config.default_duration_seconds

        return max(1.0, min(self.config.max_duration_seconds, float(value)))

    def _prepare_prompt(self, prompt: str) -> str:
        text = prompt.strip()

        if not text:
            text = "short loopable fantasy game background music, clean instrumental, no vocals"

        return text

    def _trim_wav_tensor(self, wav_tensor: torch.Tensor, sample_rate: int, duration_seconds: float) -> torch.Tensor:
        target_samples = max(1, int(sample_rate * duration_seconds))

        if wav_tensor.dim() == 1:
            return wav_tensor[:target_samples]

        if wav_tensor.dim() == 2:
            return wav_tensor[:, :target_samples]

        raise RuntimeError(f"Unexpected audio tensor shape: {tuple(wav_tensor.shape)}")

    def _tensor_to_wav_bytes(self, wav_tensor: torch.Tensor, sample_rate: int) -> bytes:
        if wav_tensor.dim() == 1:
            audio = wav_tensor.numpy()
        elif wav_tensor.dim() == 2:
            audio = wav_tensor.numpy().T
        else:
            raise RuntimeError(f"Unexpected audio tensor shape: {tuple(wav_tensor.shape)}")

        audio = np.asarray(audio, dtype=np.float32)
        audio = np.clip(audio, -1.0, 1.0)

        audio_i16 = (audio * 32767.0).astype(np.int16)

        buffer = BytesIO()
        wavfile.write(buffer, sample_rate, audio_i16)

        return buffer.getvalue()
