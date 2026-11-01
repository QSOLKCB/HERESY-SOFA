import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
RECEIPTS = ROOT / "receipts" / "generated"
RECEIPT_SCHEMA_VERSION = 1


class ExperimentError(Exception):
    """Raised when an experiment or its receipt cannot be processed."""


def discover_experiments():
    experiments = []
    for manifest_path in sorted(EXPERIMENTS.glob("HERESY-*/experiment.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ExperimentError("invalid manifest {}: {}".format(manifest_path, error))
        experiment_id = manifest.get("id")
        if experiment_id != manifest_path.parent.name:
            raise ExperimentError("manifest ID does not match directory {}".format(manifest_path.parent.name))
        if manifest.get("status") not in ("implemented", "placeholder"):
            raise ExperimentError("{} has an unsupported status".format(experiment_id))
        experiments.append(manifest)
    return experiments


def _find_experiment(experiment_id):
    for experiment in discover_experiments():
        if experiment["id"] == experiment_id:
            if experiment["status"] != "implemented":
                raise ExperimentError("{} is a placeholder and cannot be run".format(experiment_id))
            entrypoint = (EXPERIMENTS / experiment_id / experiment.get("entrypoint", "")).resolve()
            experiment_dir = (EXPERIMENTS / experiment_id).resolve()
            if experiment_dir not in entrypoint.parents or not entrypoint.is_file():
                raise ExperimentError("{} has no valid entrypoint".format(experiment_id))
            return experiment, entrypoint
    raise ExperimentError("unknown experiment {}".format(experiment_id))


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence_paths(experiment, entrypoint):
    manifest_path = EXPERIMENTS / experiment["id"] / "experiment.json"
    return sorted((manifest_path, entrypoint))


def _receipt_path(experiment_id, receipt_dir=None):
    directory = Path(receipt_dir) if receipt_dir is not None else RECEIPTS
    return directory / (experiment_id + ".json")


def run_experiment(experiment_id, receipt_dir=None):
    experiment, entrypoint = _find_experiment(experiment_id)
    evidence = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
        }
        for path in _evidence_paths(experiment, entrypoint)
    ]
    command = ["python3", str(entrypoint.relative_to(ROOT))]
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
    }
    with tempfile.TemporaryDirectory(prefix="heresy-") as working_directory:
        try:
            process = subprocess.run(
                [sys.executable, str(entrypoint)],
                cwd=working_directory,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=False,
            )
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as error:
            exit_code = 124
            stdout = (error.stdout or b"").decode("utf-8", errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = "experiment exceeded 60 seconds"
    try:
        observations = json.loads(stdout)
    except ValueError:
        observations = {"stdout": stdout, "stderr": stderr}

    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "experiment_id": experiment_id,
        "status": "executed" if exit_code == 0 else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "sqlite": sqlite3.sqlite_version,
        },
        "command": command,
        "exit_code": exit_code,
        "observations": observations,
        "evidence": evidence,
    }
    destination = _receipt_path(experiment_id, receipt_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("{}: {} (exit {})".format(experiment_id, receipt["status"], exit_code))
    print("receipt: {}".format(destination))
    return 0 if exit_code == 0 else 1


def _validate_receipt(receipt, experiment_id):
    required = {
        "schema_version",
        "experiment_id",
        "status",
        "generated_at",
        "runtime",
        "command",
        "exit_code",
        "observations",
        "evidence",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise ExperimentError("receipt fields do not match the schema")
    if (
        type(receipt["schema_version"]) is not int
        or receipt["schema_version"] != RECEIPT_SCHEMA_VERSION
        or receipt["experiment_id"] != experiment_id
    ):
        raise ExperimentError("receipt version or experiment ID does not match")
    if receipt["status"] not in ("executed", "failed"):
        raise ExperimentError("receipt has an invalid status")
    if not isinstance(receipt["generated_at"], str):
        raise ExperimentError("receipt timestamp is invalid")
    try:
        timestamp = datetime.fromisoformat(receipt["generated_at"].replace("Z", "+00:00"))
    except ValueError:
        raise ExperimentError("receipt timestamp is invalid")
    if timestamp.tzinfo is None:
        raise ExperimentError("receipt timestamp must include a timezone")
    if (
        not isinstance(receipt["exit_code"], int)
        or isinstance(receipt["exit_code"], bool)
        or not isinstance(receipt["command"], list)
        or not receipt["command"]
        or not all(isinstance(part, str) for part in receipt["command"])
    ):
        raise ExperimentError("receipt command or exit code is invalid")
    if (
        not isinstance(receipt["runtime"], dict)
        or set(receipt["runtime"]) != {"python", "platform", "sqlite"}
        or not all(isinstance(value, str) for value in receipt["runtime"].values())
        or not isinstance(receipt["observations"], (dict, list))
    ):
        raise ExperimentError("receipt runtime or observations are invalid")
    if not isinstance(receipt["evidence"], list) or not receipt["evidence"]:
        raise ExperimentError("receipt evidence is missing")
    if receipt["status"] != ("executed" if receipt["exit_code"] == 0 else "failed"):
        raise ExperimentError("receipt status does not match its exit code")


def verify_experiment(experiment_id, receipt_dir=None, quiet=False):
    experiment, entrypoint = _find_experiment(experiment_id)
    path = _receipt_path(experiment_id, receipt_dir)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ExperimentError("cannot read receipt for {}: {}".format(experiment_id, error))
    _validate_receipt(receipt, experiment_id)
    if receipt["command"] != ["python3", str(entrypoint.relative_to(ROOT))]:
        raise ExperimentError("receipt command does not match the experiment")
    actual_evidence = {
        str(item.relative_to(ROOT)): _sha256(item)
        for item in _evidence_paths(experiment, entrypoint)
    }
    recorded_evidence = {}
    for item in receipt["evidence"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "sha256"}
            or not isinstance(item["path"], str)
            or not isinstance(item["sha256"], str)
            or len(item["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in item["sha256"])
            or item["path"] in recorded_evidence
        ):
            raise ExperimentError("receipt evidence entry is invalid")
        recorded_evidence[item["path"]] = item["sha256"]
    if recorded_evidence != actual_evidence:
        raise ExperimentError("evidence hashes do not match current experiment files")
    if receipt["status"] != "executed" or receipt["exit_code"] != 0:
        raise ExperimentError("experiment receipt records a failed execution")
    if not quiet:
        print("{}: receipt and evidence verified".format(experiment_id))
    return 0


def run_all():
    result = 0
    for experiment in discover_experiments():
        if experiment["status"] == "implemented":
            result = max(result, run_experiment(experiment["id"]))
    return result


def verify_all():
    result = 0
    for experiment in discover_experiments():
        if experiment["status"] == "implemented":
            try:
                verify_experiment(experiment["id"])
            except ExperimentError as error:
                print("harness: {}".format(error), file=sys.stderr)
                result = 1
    return result
