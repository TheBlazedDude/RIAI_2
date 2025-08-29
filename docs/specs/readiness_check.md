# Readiness Check — Offline AI Workspace Gate

Version: 1

Purpose: Define the preconditions to enter the AI Workspace (Site 3). If any item fails, block entry with a clear, actionable message and link to local logs.

Scope: Applies to the pending workspace selection and all mapped models across capabilities.

Checklist (all must pass)
1) Module Discovery
- Condition: All selected modules exist under modules\<module>\manifest.json and validate against docs\specs\module_manifest_schema.json.
- Fail (error_code: manifest_invalid): “Module manifest <module> is invalid.”
  - Hint: Validate fields; see schema. Logs: artifacts\logs\modules.txt

2) Compatibility Mapping
- Condition: For each selected module, exactly one compatible model is mapped (capability, task, io_schema, resources).
- Fail (error_code: mapping_incomplete): “Module <module> is not Ready.”
  - Hint: Use Site 2 to map a compatible model. Logs: artifacts\logs\workspace.txt

3) Registry Entries
- Condition: Registry files exist:
  - registry\models\<model_id>.json
  - registry\neural_nets\<nn_id>.json (unless retrieval-only without NN)
  - registry\datasets\<dataset_id>.json for all referenced datasets
- Fail (error_code: registry_missing): “Missing registry entry <path>.”
  - Hint: Recreate or import registry entries. Logs: artifacts\logs\registry.txt

4) Dataset Availability & Checksums
- Condition: All dataset files listed in registry\datasets\*.json exist; SHA256 matches hashes.json.
- Fail (error_code: dataset_checksum_mismatch): “Dataset checksum mismatch: <file>.”
  - Hint: Regenerate synthetic dataset with the same seed or re-import. Logs: artifacts\logs\datasets.txt

5) Model Artifacts
- Condition: All model artifacts exist (checkpoints, reports) and checksums match.
- Fail (error_code: artifact_missing): “Missing artifact: <file>.”
  - Hint: Re-run training/evaluation or import artifacts. Logs: artifacts\logs\artifacts.txt

6) WordNet Bootstrap (if chat selected)
- Condition: artifacts\indices\wordnet-lexicon.jsonl exists (built once) and artifacts\datasets\wordnet_synth_<seed>.jsonl exists (if chat-core used).
- Fail (error_code: wordnet_index_missing): “WordNet index not found.”
  - Hint: Run the first-run setup to build index and generate synthetic dialogs. Logs: artifacts\logs\wordnet.txt

7) Guardrails Configuration
- Condition: guardrails policy has valid values (max_tokens ≥1; PII regex array present if PII filter ON; allowed_file_types non-empty for file-enabled modules).
- Fail (error_code: guardrails_invalid): “Guardrails policy invalid.”
  - Hint: Open Guardrails panel to correct values. Logs: artifacts\logs\guardrails.txt

8) Permissions
- Condition: Modules requiring camera/microphone/filesystem have permissions acknowledged locally.
- Fail (error_code: permission_denied): “Permission not granted: <permission> for <module>.”
  - Hint: Grant permission or disable the module. Logs: artifacts\logs\permissions.txt

9) Resource Fit
- Condition: Total resource requirements (RAM/VRAM) fit within local limits.
- Fail (error_code: resources_insufficient): “Insufficient resources (needed VRAM: x MB).”
  - Hint: Choose a lighter model or disable modules. Logs: artifacts\logs\resources.txt

10) Offline Mode
- Condition: No network calls will be attempted after entering Site 3. Optional: enforce a local firewall rule or dry-run to detect network I/O calls.
- Fail (error_code: network_access_detected): “Potential network access detected.”
  - Hint: Disable online features or pre-cache assets. Logs: artifacts\logs\network.txt

11) Writable Artifacts
- Condition: artifacts\metrics and artifacts\traces directories are writable.
- Fail (error_code: filesystem_readonly): “Artifacts directory not writable.”
  - Hint: Fix permissions or path. Logs: artifacts\logs\fs.txt

Blocking Modal Copy
- Title: “Readiness Check Failed”
- Body: List failing items with error_code, human_message, hint, where_to_find_logs.
- Actions: “Retry Readiness Check” (re-runs), “Open Logs Folder”, “Learn how to fix this” (opens local docs).

Determinism & Reproducibility
- Record seeds for all synthetic generations and evaluations. Compare against registry entries.
- Any seed mismatch is a warning (error_code: seed_mismatch_warning) unless it breaks checksums.
