from importlib.metadata import PackageNotFoundError, version

from sornaris.cache import BisectCache
from sornaris.cache import make_cache_key
from sornaris.cli import main
from sornaris.cli import load_prompts_jsonl
from sornaris.cli import load_evals_jsonl
from sornaris.cli import report_to_dict
from sornaris.models import AxisType
from sornaris.models import PromptVersion
from sornaris.models import ModelVersion
from sornaris.models import EvalExample
from sornaris.models import EvalResult
from sornaris.models import BisectStep
from sornaris.models import BisectReport
from sornaris.models import prompt_version_hash
from sornaris.multi import bisect_multi_axis
from sornaris.providers import BaseProvider
from sornaris.providers import FakeProvider
from sornaris.providers import ScriptedProvider
from sornaris.providers import OpenAIProvider
from sornaris.providers import AnthropicProvider
from sornaris.providers import ProviderError
from sornaris.providers import build_provider
from sornaris.runner import run_eval
from sornaris.scoring import ExactMatchScorer
from sornaris.scoring import ContainsScorer
from sornaris.scoring import RegexScorer
from sornaris.scoring import CallableScorer
from sornaris.scoring import aggregate_mean
from sornaris.scoring import aggregate_pass_rate
from sornaris.search import bisect_single_axis

try:
    __version__ = version("sornaris")
except PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "BisectCache",
    "make_cache_key",
    "main",
    "load_prompts_jsonl",
    "load_evals_jsonl",
    "report_to_dict",
    "AxisType",
    "PromptVersion",
    "ModelVersion",
    "EvalExample",
    "EvalResult",
    "BisectStep",
    "BisectReport",
    "prompt_version_hash",
    "bisect_multi_axis",
    "BaseProvider",
    "FakeProvider",
    "ScriptedProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "ProviderError",
    "build_provider",
    "run_eval",
    "ExactMatchScorer",
    "ContainsScorer",
    "RegexScorer",
    "CallableScorer",
    "aggregate_mean",
    "aggregate_pass_rate",
    "bisect_single_axis",
]
