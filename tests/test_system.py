from __future__ import annotations
from pathlib import Path
import json
import re
import shutil
from typing import List, Dict

from app.backend.main import (
    ROOT,
    health,
    list_modules,
    readiness,
    save_workspace,
    train_job,
    evaluate_job,
    save_mappings,
    set_guardrails,
    runtime_post,
    create_neural_net,
    create_model,
)
from app.backend.core.utils.io import (
    ARTIFACTS_DIR, ARTIFACTS_METRICS, ARTIFACTS_INDICES, ARTIFACTS_DATASETS,
    REGISTRY_DIR, REGISTRY_WS_DIR, REGISTRY_MODELS_DIR, REGISTRY_NN_DIR,
    WORDNET_ROOT
)
from app.backend.core.registry.datasets import register_dataset, verify_dataset


def _cleanup_files(paths: List[Path]):
    for p in paths:
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink(missing_ok=True)
        except Exception:
            pass


def _parse_yaml_ids(yaml_path: Path) -> List[str]:
    # Minimal parser: extract lines like "- id: something" under architectures
    ids: List[str] = []
    if not yaml_path.exists():
        return ids
    for line in yaml_path.read_text(encoding='utf-8', errors='ignore').splitlines():
        m = re.match(r"\s*-\s+id:\s*([a-zA-Z0-9_\-]+)", line)
        if m:
            ids.append(m.group(1))
    return ids


def test_health_and_modules_and_readiness_initial():
    # Health
    r = health()
    assert r.get('status') == 'ok'

    # Modules
    m = list_modules()
    mods = [x['id'] for x in m.get('modules', []) if isinstance(x, dict) and x.get('id')]
    assert 'lexicon-wordnet3' in mods and 'chat-core' in mods and 'predictor-finance' in mods

    # Readiness with no selection
    rd = readiness()
    assert 'status' in rd and 'errors' in rd
    # WordNet root should exist per repo structure
    assert (ROOT / 'WordNet-3.0').exists()


def test_bootstrap_flow_end_to_end(tmp_path: Path):
    # Save workspace selection
    selection = {'selected_modules': ['chat-core', 'predictor-finance']}
    ws = save_workspace(selection)
    assert ws.get('ok') is True

    seed = 1337
    # Train all base modules
    for mid in ['lexicon-wordnet3', 'chat-core', 'predictor-finance']:
        j = train_job({'module_id': mid, 'seed': seed})
        assert j.get('ok') is True

    # Save mappings for chat and predictor
    mappings = {
        'module_map': {
            'chat-core': f'chat_retrieval_{seed}',
            'predictor-finance': f'predictor_ma_{seed}',
        }
    }
    maps = save_mappings(mappings)
    assert maps.get('mappings') and maps['mappings']['module_map']['chat-core'].endswith(str(seed))

    # Evaluate
    j = evaluate_job({'module_id': 'chat-core', 'seed': seed, 'model_id': f'chat_retrieval_{seed}'})
    assert j.get('ok') is True
    j = evaluate_job({'module_id': 'predictor-finance', 'seed': seed, 'model_id': f'predictor_ma_{seed}'})
    assert j.get('ok') is True

    # Metrics files exist
    chat_metrics = ARTIFACTS_METRICS / 'chat' / f'chat_retrieval_{seed}.json'
    pred_metrics = ARTIFACTS_METRICS / 'predictor' / f'predictor_ma_{seed}.json'
    assert chat_metrics.exists() and pred_metrics.exists()

    # Readiness ready
    rd = readiness()
    assert rd.get('status') == 'ready'


def test_neural_networks_catalog_and_model_mapping_cleanup():
    # Parse catalog and pick first NN id
    catalog_path = ROOT / 'neural_networks.yaml'
    ids = _parse_yaml_ids(catalog_path)
    assert len(ids) > 0
    nn_id = f"test_{ids[0]}"

    # Create NN via API
    res = create_neural_net({'id': nn_id, 'name': nn_id, 'family': 'test'})
    assert res.get('ok') is True

    # Create a model that references this NN (for chat-core)
    model_id = f"chat_model_{nn_id}"
    res = create_model({
        'id': model_id,
        'name': model_id,
        'capability': 'chat',
        'task': 'dialogue',
        'nn_id': nn_id
    })
    assert res.get('ok') is True

    # Map it to chat-core and evaluate
    res = save_mappings({'module_map': {'chat-core': model_id}})
    assert res.get('mappings') and res['mappings']['module_map']['chat-core'] == model_id

    # Evaluate chat-core for this model id with a fixed seed
    seed = 2025
    res = evaluate_job({'module_id': 'chat-core', 'seed': seed, 'model_id': model_id})
    assert res.get('ok') is True

    # Readiness should not complain about missing NN because we created it
    rd = readiness()
    assert 'errors' in rd
    # Ensure no registry_missing for this nn_id
    errs = [e for e in rd['errors'] if isinstance(e, dict) and e.get('error_code') == 'registry_missing' and e.get('nn_id') == nn_id]
    assert len(errs) == 0

    # Cleanup: remove model and nn registry entries and metrics for this model
    _cleanup_files([
        REGISTRY_MODELS_DIR / f"{model_id}.json",
        REGISTRY_NN_DIR / f"{nn_id}.json",
        ARTIFACTS_METRICS / 'chat' / f"{model_id}.json",
    ])


def test_guardrails_truncate_and_pii_mask():
    # Set guardrails policy
    policy = {
        'max_tokens': 5,
        'pii_regex': [r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"],
        'blocked_categories': ['violence'],
        'allowed_file_types': ['.txt']
    }
    res = set_guardrails(policy)
    assert res.get('ok') is True

    text = "This contains SSN 123-45-6789 and many tokens that should be truncated beyond the limit."
    res = runtime_post({'text': text})
    processed = res.get('processed')
    assert processed and isinstance(processed, dict)
    actions = [a['type'] for a in processed.get('actions', [])]
    assert 'pii_mask' in actions
    assert 'truncate' in actions


def test_dataset_register_and_verify():
    # Register OHLCV sample dataset into registry and verify checksum
    csv_path = ROOT / 'app' / 'modules' / 'predictor-finance' / 'data' / 'samples' / 'ohlcv.csv'
    assert csv_path.exists()
    entry = register_dataset('test_ohlcv', 'Test OHLCV', [csv_path])
    problems = verify_dataset(entry)
    assert problems == []
    # Cleanup registry dataset entry
    (REGISTRY_DIR / 'datasets' / 'test_ohlcv.json').unlink(missing_ok=True)



def test_train_with_nn_binding():
    # Create a test NN with a specific family to influence training hyperparameters
    nn_id = 'test_family_nlp'
    res = create_neural_net({'id': nn_id, 'name': nn_id, 'family': 'nlp_transformer'})
    assert res.get('ok') is True

    # Train chat-core with this NN
    seed = 777
    job = train_job({'module_id': 'chat-core', 'seed': seed, 'nn_id': nn_id})
    assert job.get('ok') is True
    model_id = job['job']['result']['model_id']

    # Model entry should include nn_id
    model_path = REGISTRY_MODELS_DIR / f"{model_id}.json"
    assert model_path.exists()
    obj = json.loads(model_path.read_text(encoding='utf-8'))
    assert obj.get('nn_id') == nn_id

    # Evaluate this model id
    job2 = evaluate_job({'module_id': 'chat-core', 'seed': seed, 'model_id': model_id})
    assert job2.get('ok') is True

    # Cleanup for isolation
    (REGISTRY_NN_DIR / f"{nn_id}.json").unlink(missing_ok=True)
    (REGISTRY_MODELS_DIR / f"{model_id}.json").unlink(missing_ok=True)
    (ARTIFACTS_METRICS / 'chat' / f"{model_id}.json").unlink(missing_ok=True)
