import os

_brew_bin = "/opt/homebrew/bin"
if _brew_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _brew_bin + ":" + os.environ.get("PATH", "")

import torch as _torch

_orig_load = _torch.load


def _permissive_load(*a, **kw):
    kw.setdefault("weights_only", False)
    return _orig_load(*a, **kw)


_torch.load = _permissive_load

import gigaam

GIGAAM_MODEL = os.getenv("GIGAAM_MODEL", "v2_rnnt")

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = gigaam.load_model(GIGAAM_MODEL)
    return _model


def transcribe_gigaam(audio_path: str) -> str:
    model = _get_model()
    return model.transcribe(audio_path)
