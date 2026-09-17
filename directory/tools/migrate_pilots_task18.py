#!/usr/bin/env python3
"""Phase B pilot migration (task #18) — Openkod authoring draft.

Writes additive schema_version-2 blocks into the eight admitted pilot setup
records only. Every fact is quoted from the archived corpus; nothing is
inferred. Existing values/prose/tiers are never changed or reordered; new
measurements are appended only where a comparison needs the other documented
arm. Pilot 02 is the only C3 author-reported matched comparison and is never
called verified; no pilot gets reproduction language.
"""
import json
import os

D = 'directory/data/setups/'

def load(pid):
    with open(D + pid + '.json', encoding='utf-8') as fh:
        return json.load(fh)

def save(pid, s):
    with open(D + pid + '.json', 'w', encoding='utf-8') as fh:
        json.dump(s, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

def mnext(s):
    ids = sorted(int(m['id'][1:]) for m in s['measurements'])
    return f"m{ids[-1]+1:03d}"

def add_meas(s, lineage, *, metric, value, unit, context, provenance, date,
             source, method_grade, level='c2_observation', concurrency=1,
             conditions=None, note=None):
    m = {
        'id': mnext(s),
        'metric': metric,
        'value': value,
        'unit': unit,
        'provenance': provenance,
        'date': date,
        'source': source,
        'concurrency': concurrency,
        'context': context,
    }
    if note is not None:
        m['note'] = note
    if conditions:
        m['conditions'] = conditions
    m['evidence'] = {
        'level': level,
        'method_grade': method_grade,
        'quality_status': 'unchecked',
        'lineage_id': lineage,
        'dossier_cited': True,
    }
    s['measurements'].append(m)
    return m['id']

def set_all_meas_evidence(s, evidence_by_id, conditions_by_id=None,
                          default_lineage=None, default_grade='author_report',
                          default_level='c2_observation'):
    for m in s['measurements']:
        mid = m['id']
        ev, cond = evidence_by_id(mid, evidence_by_id)
        if cond is not None:
            m['conditions'] = cond
            if cond.get('concurrency') is None:
                cond.pop('concurrency', None)
        if ev is not None:
            m['evidence'] = ev

def apply_on(m, evidence=None, conditions=None):
    if evidence:
        m['evidence'] = dict(evidence)
        m['evidence']['dossier_cited'] = True
    if conditions:
        m['conditions'] = dict(conditions)
    if 'condition_completeness' in (conditions or {}):
        raise SystemExit('derivation must not be stored')

# the leftover unit artifacts removed
def pilot_01():
    P = 'qwen38-flash-next-nvidia-nvfp4-vllm-2x-spark'
    s = load(P)
    s['schema_version'] = 2
    repo = 'https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks'
    s['evidence'] = {
        'rubric_version': '1.0',
        'lineages': [{
            'id': 'mia-ai-lab-dual-spark',
            'actor': 'MiaAI-Lab',
            'publisher': 'mia-ai-lab',
            'kind': 'builder_repo',
            'sources': [repo, 'https://x.com/MiaAI_lab/status/2092670516964270101'],
            'locator': 'README server-read tables; announcement post',
            'archive_path': 'directory/tools/history/inputs/pass4-social/raw/repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md',
            'note': 'README and X announcement are one lineage.',
        }],
        'claims': [
            {'id': 'tp2-ep-roce-configuration',
             'technique_id': 'roce-tensor-parallel',
             'kind': 'configuration',
             'statement': 'Serves the NVFP4 checkpoint across two GB10 nodes with TP2 + EP + MTP3 over ConnectX RoCE/IB, passwordless SSH and Docker on both nodes.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'mia-ai-lab-dual-spark',
             'source': repo,
             'locator': 'README launch section (lines 10/37/405)',
             'quote': 'Multi-node inference for [RadixArk/Qwen3.8-Flash-Next-NVFP4] across 2 DGX Sparks using vLLM with TP2+EP+MTP3.',
             'status': 'recorded'},
            {'id': 'native-mtp-draft-head-usage',
             'technique_id': 'native-mtp',
             'kind': 'mechanism',
             'statement': 'Uses the checkpoint MTP-3 speculative head; the MTP layer-index alias is re-injected by start.sh so the loader binds mtp.layers.48 correctly.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'mia-ai-lab-dual-spark',
             'source': repo,
             'locator': 'README checkpoint-fix notes (start.sh section)',
             'status': 'recorded'},
            {'id': 'fp8-routed-experts-failure',
             'technique_id': 'fp8-block-scales-routed-experts',
             'kind': 'failure_mode',
             'statement': 'Without the FP8_BLOCK_SCALES routed-experts patch, the MoE can load unquantized and die roughly seven minutes in.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'mia-ai-lab-dual-spark',
             'source': repo,
             'locator': 'README patch notes (line 89 region)',
             'quote': 'FP8_BLOCK_SCALES routed-experts patch (missing upstream — without it the MoE loads unquantized and dies ~7 min in)',
             'status': 'recorded'},
        ],
        'comparisons': [{
            'id': 'mtp-off-vs-mtp3',
            'question': 'What association does the README table report between MTP off and MTP=3 at batch 1?',
            'candidate_variable': 'engine MTP toggle (native MTP=3 draft head)',
            'a': {'label': 'MTP off', 'measurement_id': 'm001'},
            'b': {'label': 'MTP=3', 'measurement_id': 'm002'},
            'result': 'b_better',
            'effect_metric': 'decode_per_stream',
            'effect_direction': 'increase',
            'contrast_kind': 'uncontrolled',
            'conditions_constant': [
                'two-node GB10 box as recorded',
                'batch-1 greedy as labelled in the README server-read table',
                'same MiaAI-Lab README server-telemetry source',
            ],
            'conditions_unstated': [
                'raw full A/B command',
                'prompt corpus',
                'exact context tokens',
                'sample size / n',
                'same server configuration and workload across both arms',
                'MTP toggle as sole changed variable',
                'checkpoint-path discrepancy resolution',
                'repo/build pin',
            ],
            'evidence_level': 'c2_observation',
            'lineage_id': 'mia-ai-lab-dual-spark',
            'independent_reproductions': [],
            'quality_status': 'unchecked',
            'source': repo,
            'locator': 'README server-read benchmark table',
            'promotion_gate': {
                'target_level': 'c3_matched_ab',
                'target_contrast_kind': 'single_variable',
                'required_facts': [
                    'both arms identified',
                    'same server configuration and workload',
                    'MTP is the sole toggled variable',
                    'checkpoint-path discrepancy resolved',
                ],
                'status': 'not_met',
                'note': 'Pinning alone is not enough. If the four facts cannot be established from existing artifacts, a clean 2x Spark rerun is required for C3 (Terra 2026-09-16).',
            },
            'provenance': 'forum',
            'date': '2026-08-26',
        }],
        'contradictions': [{
            'id': 'tweet-vs-readme',
            'statement': 'Announcement says ~64 tok/s single stream and ~115 tok/s at 2-4 concurrent; README server tables record 52.1-54.4 batch-1 and 86.5-128.1 aggregate at x2-x4.',
            'resolution': 'Repo numbers admitted under law 9; tweet remains discovery-only.',
            'status': 'resolved_by_source_priority',
            'sources': [repo, 'https://x.com/MiaAI_lab/status/2092670516964270101'],
            'lineage_ids': ['mia-ai-lab-dual-spark'],
        }],
        'open_questions': [{
            'id': 'repo-pin-ambiguous',
            'question': 'No repo commit exists on or before the 2026-08-26 recipe anchor; the earliest available bootstrap commit is 6e08722d1fad (2026-08-31).',
            'blocks': ['exact_reproduction'],
            'owner': 'openkod',
            'type': 'other',
            'status': 'open',
            'source': 'docs/builder-concerns-2026-09-16/pilot-dossiers/00-INDEX.md',
            'locator': 'historically-resolved pin table, MiaAI-Lab row',
        }],
        're_review_triggers': [
            'vLLM version or container digest changes',
            'checkpoint identity changes between the nvidia and RadixArk paths',
            'FP8 routed-experts patch lands upstream vLLM',
        ],
    }
    # per-measurement conditions/evidence
    ev0 = {'level': 'c2_observation', 'method_grade': 'server_telemetry',
           'lineage_id': 'mia-ai-lab-dual-spark', 'quality_status': 'unchecked',
           'dossier_cited': True}
    byid = {m['id']: m for m in s['measurements']}
    c_m1 = {'hardware_count': 2, 'greedy': True, 'kv_dtype': 'fp8_e4m3',
            'context_label': 'batch-1 greedy, MTP OFF (README checkpoint table)'}
    c_m2 = {'hardware_count': 2, 'greedy': True, 'kv_dtype': 'fp8_e4m3',
            'context_label': 'batch-1 greedy, MTP=3 (README table)',
            'spec_decode': 'mtp', 'max_draft_tokens': 3}
    c_mtail = {'hardware_count': 2, 'spec_decode': 'mtp', 'kv_dtype': 'fp8_e4m3'}
    for mid, cond in (('m001', c_m1), ('m002', c_m2)):
        byid[mid]['conditions'] = cond
        byid[mid]['evidence'] = dict(ev0, level='c2_observation')
    for mid in ('m003', 'm004', 'm005', 'm006', 'm007'):
        byid[mid]['conditions'] = dict(c_mtail)
        byid[mid]['evidence'] = dict(ev0, level='c2_observation')
    byid['m003']['evidence']['dossier_cited'] = True
    byid['m008']['evidence'] = {'level': 'c2_observation',
                                'method_grade': 'server_telemetry',
                                'lineage_id': 'mia-ai-lab-dual-spark',
                                'quality_status': 'unchecked',
                                'dossier_cited': True}
    byid['m008']['conditions'] = {'hardware_count': 2,
                                  'context_label': 'weights resident per node',
                                  'spec_decode': 'mtp'}
    # memory profile + offload none + interconnect
    s['requirements']['memory_profile'] = {
        'kv_dtype': 'fp8_e4m3',
        'gpu_memory_utilization': 0.835,
        'provenance': 'forum',
        'date': '2026-08-26',
        'source': repo,
        'locator': 'README server-read tables (checkpoint table + MEMORY row)',
        'entries': [
            {'component': 'weights', 'value': 62.72, 'unit': 'GB', 'scope': 'per_unit',
             'location': 'gpu', 'provenance': 'forum', 'date': '2026-08-26',
             'source': repo, 'locator': 'README checkpoint/memory table',
             'note': 'weights resident per node (64.3 GiB with MTP)'},
            {'component': 'kv_pool', 'value': 32.02, 'unit': 'GiB', 'scope': 'per_unit',
             'location': 'gpu', 'kv_tokens': 3652200, 'provenance': 'forum',
             'date': '2026-08-26', 'source': repo,
             'locator': 'README KV pool row (~3.65 million tokens fp8)',
             'note': '32.02 GiB = 3,652,200 tokens; ~13.9x the 262K ceiling'},
        ],
    }
    s['requirements']['offload'] = {
        'strategy': 'nfs_weight_share',
        'intentional': True,
        'cold_start_effect': None,
        'source': repo,
        'locator': 'README weight-sharing options: rsync, or NFS with --nfs',
        'provenance': 'forum',
        'date': '2026-08-26',
        'note': 'weights are shared to the worker via rsync or NFS; PLE_OFFLOAD=false in the served configuration',
    }
    s['interconnect'] = {
        'kind': 'roce', 'role': 'tensor_parallel',
        'topology': 'ConnectX between two GB10 nodes; TP2+EP+MTP3 with rank-1 launch via start.sh',
        'requires_same_fabric': True, 'provenance': 'forum', 'date': '2026-08-26',
        'source': repo, 'locator': 'README multi-node provision/launch section',
    }
    # engine runtime pin + spec profile
    s['engine']['image_digest'] = ('sha256:d464f3b4 (prefix; the full digest is not in the public tag list, '
                                   'archived at README line 405)')
    s['engine']['fork_revision'] = {
        'repo': 'https://github.com/vllm-project/vllm',
        'branch': 'dev (qwen38-flash-next container build)',
        'anchor_date': '2026-08-26',
        'resolution': 'unresolved',
        'ambiguous': True,
        'source': repo,
        'locator': 'the dual-Spark build is a ~20.6 GB NVIDIA dev container; only the image-digest prefix is archived (README line 405)',
        'retrieved': '2026-09-16',
    }
    s['engine']['environment'] = {'os': 'DGX OS (Ubuntu 26.04-class host per README container note)',
                                  'source': repo, 'locator': 'README container section',
                                  'date': '2026-08-26'}
    s['run']['repo_revision'] = {
        'anchor_date': '2026-08-26',
        'resolution': 'earliest_commit_after_anchor',
        'ambiguous': True,
        'source': repo,
        'locator': 'earliest available commit (2026-08-31) postdates the anchor; git history has no commit on/before it',
        'retrieved': '2026-09-16',
        'note': 'no commit exists on/before the 2026-08-26 anchor; the repo was bootstrapped five days later',
    }
    s['engine']['spec_decode_profile'] = {
        'method': 'mtp',
        'max_draft_tokens': 3,
        'acceptance_rate_pct': 72.8,
        'acceptance_basis': '823 of 1131 is the builder-quoted acceptance count; number kept vendor-attributed from the server-read table',
        'date': '2026-08-26',
        'source': repo,
        'locator': 'README server-read table (m002 2.13x line; acceptance 823/1131)',
        'provenance': 'forum',
    }
    # sources lineage ids
    for src in s['sources']:
        src['lineage_id'] = 'mia-ai-lab-dual-spark'
        if src['url'] == repo:
            src['archive_path'] = 'directory/tools/history/inputs/pass4-social/raw/repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md'
            src['locator'] = 'README server-read benchmark tables'
        if 'status/2092670516964270101' in src.get('url', ''):
            src['archive_path'] = 'directory/tools/history/inputs/pass4-social/raw/xsweep_NVIDIAAI.json'
            src['locator'] = 'thread payload archived in the NVIDIAAI sweep raw file'
    s['sources'].append({
        'url': repo + '/blob/main/README.md',
        'kind': 'docs',
        'note': 'durable README: measurement-conditions tables',
        'lineage_id': 'mia-ai-lab-dual-spark',
        'archive_path': 'directory/tools/history/inputs/pass4-social/raw/repo_MiaAI-Lab_Flash-Next-Dual-DGX-Sparks_README.md',
    })
    save(P, s)

# ---------------------------------------------------------------- pilot 02
def pilot_02():
    P = 'qwen38-27b-unsloth-gguf-dflash2-llamacpp-4090'
    s = load(P)
    s['schema_version'] = 2
    post1 = 'https://x.com/analogalok/status/2089979723166200196'
    post2 = 'https://x.com/analogalok/status/2090874243185856971'
    pr = 'https://github.com/ggml-org/llama.cpp/pull/27342'
    s['evidence'] = {
        'rubric_version': '1.0',
        'lineages': [{
            'id': 'analogalok-4090-dflash2',
            'actor': 'analogalok',
            'publisher': 'analogalok',
            'kind': 'builder_thread',
            'sources': [post1, post2,
                        'https://x.com/analogalok/status/2090797011100717267',
                        'https://x.com/analogalok/status/2090400471458759145'],
            'locator': 'DFlash2 series posts (one builder lineage)',
            'note': 'The 08-19 and 08-21 posts plus the patch explainer threads are one builder lineage.',
        }],
        'claims': [
            {'id': 'dflash2-drafter-mechanism',
             'technique_id': 'dflash2-block-diffusion-drafting',
             'kind': 'mechanism',
             'statement': 'DFlash2 uses parallel block-diffusion drafting to propose a block of tokens for the target model to verify, replacing the stock Q4_K_M per-token draft.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'analogalok-4090-dflash2',
             'source': pr,
             'locator': 'PR #27342 description / archived builder post',
             'status': 'recorded'},
            {'id': 'q2-drafter-swap-config',
             'technique_id': 'dflash2-block-diffusion-drafting',
             'kind': 'configuration',
             'statement': 'Run with --parallel 1, --spec-draft-n-max 4, KV q4q8 ladder, and the custom analogalok Q2_K (~700MB) drafter so the same 16.7 GB build reaches ~250k context.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'analogalok-4090-dflash2',
             'source': 'https://x.com/analogalok/status/2090797011100717267',
             'locator': 'archived post 2090797011100717267 (--parallel 1 unlock)',
             'status': 'recorded'},
            {'id': 'mtp-kv-on-accelerated-prefill-is-worse-than-dflash2',
             'technique_id': 'native-mtp',
             'kind': 'performance_effect',
             'statement': 'Native MTP beats DFlash2 on prefill (2,324 vs 1,662 tok/s at 26k), a negative recorded for the DFlash2 lane.',
             'evidence_level': 'c2_observation',
             'lineage_id': 'analogalok-4090-dflash2',
             'source': post2,
             'locator': 'raw/xsweep_analogalok.json, 2026-08-21 18:50z post',
             'measurement_ids': ['m005'],
             'status': 'recorded'},
        ],
        'comparisons': [{
            'id': 'dflash2-vs-native-mtp-decode-26k',
            'question': "What does the builder's stated protocol report for DFlash2 versus native MTP decode at the 26k prompt baseline?",
            'variable': 'speculative_drafter',
            'a': {'label': 'native MTP (same box / quant / KV / prompt set)',
                  'measurement_id': None},
            'b': {'label': 'DFlash2 (custom 2-bit Q2_K drafter)',
                  'measurement_id': None},
            'result': 'b_better',
            'effect_metric': 'decode_per_stream',
            'effect_direction': 'increase',
            'contrast_kind': 'single_variable',
            'conditions_constant': [
                'single RTX 4090 24 GB box',
                'same checkpoint/quant family as recorded',
                'same KV q4/q8 configuration as recorded',
                'same 26k prompt baseline',
                '--parallel 1',
            ],
            'conditions_unstated': [
                'exact llama.cpp binary/build used by each arm',
                'whether native MTP ran mainline or a different fork commit',
                'sample size / n',
                'driver/runtime pins',
            ],
            'evidence_level': 'c3_matched_ab',
            'binary_provenance_status': 'unresolved',
            'lineage_id': 'analogalok-4090-dflash2',
            'independent_reproductions': [],
            'quality_status': 'unchecked',
            'source': post2,
            'locator': 'raw/xsweep_analogalok.json, 2026-08-21 18:50z post',
            're_review_triggers': [
                'native-MTP baseline commit/build is pinned',
                'DFlash2 fork commit/build is pinned',
                'an independent lineage reruns both arms',
            ],
            'note': "Scoped author-reported matched comparison. Do not render as verified, proved, independently reproduced, or generally causal across builds.",
            'date': '2026-08-21',
            'provenance': 'forum',
        }],
        'open_questions': [],
        're_review_triggers': [],
    }
    s['evidence']['re_review_triggers'].extend([
        'native-MTP baseline commit pinned to the same llama.cpp binary as the PR #27342 arm',
        'a second lineage reruns the 26k prompt pair',
    ])
    # capabilities + known failure on PR branch
    s['capability_observations'] = [{
        'capability': 'vision', 'status': 'broken',
        'trigger': 'multimodal / mmproj path on the PR #27342 llama.cpp build as recorded in the post',
        'scope': 'this exact PR branch (single-GPU build)',
        'source': 'https://x.com/analogalok/status/2090400471458759145',
        'locator': 'raw/xsweep_analogalok.json, 2026-08-20 18:50z post',
        'quote': 'Multi GPU and multimodality is currently broken.',
        'lineage_id': 'analogalok-4090-dflash2',
    }]
    s['known_failures'] = [{
        'id': 'multi-gpu-split-broken-on-pr-branch',
        'stage': 'other',
        'trigger': "tensor-parallel split across multiple cards on llama.cpp PR #27342",
        'effect': 'load fails; the run is single-GPU only',
        'status': 'open',
        'observed_date': '2026-08-20',
        'date': '2026-08-20',
        'lineage_id': 'analogalok-4090-dflash2',
        'source': 'https://x.com/analogalok/status/2090400471458759145',
        'locator': 'raw/xsweep_analogalok.json, 2026-08-20 post (PR #27342 catch)',
        'quote': 'Multi GPU and multimodality is currently broken. Tensor splitting across multiple cards will fail on this PR.',
    }]
    # memory profile + offload
    s['requirements']['memory_profile'] = {
        'provenance': 'forum', 'date': '2026-08-19',
        'source': post1, 'locator': "builder's VRAM-ladder post (m006 context)",
        'entries': [
            {'component': 'weights', 'value': 16.7, 'unit': 'GB', 'scope': 'total',
             'location': 'gpu', 'provenance': 'forum', 'date': '2026-08-19',
             'source': post1, 'locator': 'UD-Q4_K_XL size, builder post'},
            {'component': 'other', 'value': 22.0, 'unit': 'GB', 'scope': 'total',
             'location': 'gpu', 'provenance': 'forum', 'date': '2026-08-19',
             'source': post1,
             'locator': 'm006 peak VRAM at the 30k / n-max-4 operating point',
             'note': 'resident peak of the recorded operating point; component split beyond weights is not in the source'},
        ],
    }
    s['requirements']['offload'] = {
        'strategy': 'none',
        'intentional': None,
        'cold_start_effect': None,
        'source': 'https://x.com/analogalok/status/2090797011100717267',
        'locator': "builder states the run is resident in 24 GB VRAM at the measured operating points; 'no host RAM/SSD offload' is not stated word-for-word",
        'provenance': 'forum',
        'date': '2026-08-21',
        'note': "'none' is the strongest supported reading of the recorded 22.x GB / 24 GB resident VRAM and --parallel 1, and does not prove host offload never happened.",
    }
    s['run']['repo_revision'] = {
        'resolution': 'unresolved',
        'anchor_date': '2026-08-19',
        'ambiguous': True,
        'source': pr,
        'locator': 'llama.cpp PR #27342, but the exact build used per arm is unstated',
        'retrieved': '2026-09-16',
    }
    s['engine']['fork_revision'] = {
        'repo': 'https://github.com/ggml-org/llama.cpp',
        'branch': 'PR #27342',
        'commits': None,
        'anchor_date': '2026-08-19',
        'resolution': 'unresolved',
        'ambiguous': True,
        'source': pr,
        'locator': 'the archived posts reference PR #27342 without committing to a build SHA; the native-MTP baseline arm is a different binary/build',
        'retrieved': '2026-09-16',
        'note': 'binary provenance between the DFlash2 arm and the native-MTP baseline arm is unresolved.',
    }
    s['engine']['kernel_patches'] = [{
        'id': 'dflash2-pr-27342', 'pr': '27342',
        'purpose': 'Block-diffusion DFlash2 speculative decoding that the 90-tok/s DFlash2 arm needs.',
        'source': pr, 'locator': 'llama.cpp PR #27342 description',
    }]
    s['engine']['spec_decode_profile'] = {
        'method': 'dflash2',
        'draft_checkpoint': 'z-lab/Qwen3.8-27B-DFlash2-GGUF (with the custom analogalok 2-bit Q2_K drafter)',
        'draft_revision': '57ab3265056d (DFlash 2 release, 2026-08-18 21:25Z; Q4_K_M drag blob 18a380efc9...)',
        'draft_quant': 'q4_k_m / custom 2-bit Q2_K drafter',
        'max_draft_tokens': 4,
        'acceptance_rate_pct': None,
        'source': 'docs/builder-concerns-2026-09-16/r-artifacts.md',
        'locator': 'row 3: z-lab revision resolved to the 2026-08-18 anchor',
        'date': '2026-08-19',
        'provenance': 'forum',
        'note': 'acceptance_rate_pct stays null for the 26k decoded pair (no source-stated "./acceptance" number in that post; the +5.39 acceptance figure the builder quotes is for his 30k n-max-4 explainer, not the A/B pair).',
    }

    # per-measurement conditions/evidence
    byid = {m['id']: m for m in s['measurements']}
    evg = {'level': 'c2_observation', 'method_grade': 'author_report',
           'lineage_id': 'analogalok-4090-dflash2', 'quality_status': 'unchecked',
           'dossier_cited': True}
    # m001 90 @ ~30k n-max 4
    m = byid['m001']
    m['conditions'] = {'context_label': '~30k operating point', 'greedy': None,
                       'hardware_count': 1, 'spec_decode': 'dflash2',
                       'max_draft_tokens': 4, 'workload': None}
    m['evidence'] = dict(evg, note='headline, DFlash2-vs-MTP A/B at ~30k context; quality status unchecked')
    # m002 (87.05)
    byid['m002']['conditions'] = {'context_label': '30k operating point, n-max 4',
                                  'hardware_count': 1, 'spec_decode': 'dflash2',
                                  'max_draft_tokens': 4, 'workload': None}
    byid['m002']['evidence'] = dict(evg, level='c2_observation')
    # m003 (75.66) — the DFlash2 arm of the C3-comparison
    byid['m003']['conditions'] = {'context_label': '26k prompt baseline',
                                  'workload': None, 'greedy': True,
                                  'hardware_count': 1, 'spec_decode': 'dflash2',
                                  'max_draft_tokens': 4}
    byid['m003']['evidence'] = dict(evg, level='c2_observation',
                                    contrast_id='dflash2-vs-native-mtp-decode-26k')
    # m004 (59.22 decay) — 80k prompt
    byid['m004']['conditions'] = {'context_label': '80k-prompt stress',
                                  'hardware_count': 1, 'spec_decode': 'dflash2',
                                  'max_draft_tokens': 4, 'workload': None}
    byid['m004']['evidence'] = dict(evg, level='c2_observation')
    # m005 prefill 1662 (26k, DFlash2) — native MTP 2324 side of the C3 prefill comparison
    byid['m005']['conditions'] = {'context_label': '26k prompt baseline',
                                  'workload': None, 'greedy': True,
                                  'hardware_count': 1, 'spec_decode': 'dflash2'}
    byid['m005']['evidence'] = dict(evg, level='c2_observation',
                                    contrast_id='dflash2-vs-native-mtp-prefill-26k',
                                    dossier_cited=True)
    # m006 peak VRAM
    byid['m006']['conditions'] = {'context_label': '30k / n-max-4 operating point',
                                  'hardware_count': 1, 'spec_decode': 'dflash2',
                                  'max_draft_tokens': 4}
    byid['m006']['evidence'] = {'level': 'c2_observation', 'method_grade': 'author_report',
                                'lineage_id': 'analogalok-4090-dflash2',
                                'quality_status': 'unchecked', 'dossier_cited': True,
                                'contrast_kind': 'claimed'}
    # the native-MTP arm rows (needed by the C3-comparison sides)
    mtp_row = {'level': 'c2_observation', 'method_grade': 'author_report',
               'lineage_id': 'analogalok-4090-dflash2', 'quality_status': 'unchecked',
               'dossier_cited': True,
               'note': 'Native-MTP arm of the same builder-stated protocol; '
                       'the binary/build identity is not pinned.',
               'contrast_id': 'dflash2-vs-native-mtp-decode-26k'}
    a_dec26 = add_meas(s, lineage='analogalok-4090-dflash2',
                       metric='decode_per_stream', value=68.09, unit='tok/s',
                       context='26k prompt baseline, native MTP arm of the same 08-21 protocol',
                       provenance='forum', date='2026-08-21',
                       source=post2, method_grade='author_report',
                       conditions={'context_label': '26k prompt baseline, native MTP arm',
                                   'workload': None, 'greedy': True, 'hardware_count': 1},
                       note='contrast arm; the builder does not state the native-MTP baseline build/binary.')
    a_dec80 = add_meas(s, lineage='analogalok-4090-dflash2',
                       metric='decode_per_stream', value=55.56, unit='tok/s',
                       context='80k prompt stress, native MTP arm of the same protocol',
                       provenance='forum', date='2026-08-21', source=post2,
                       method_grade='author_report',
                       conditions={'context_label': '80k-prompt stress, native MTP arm',
                                   'workload': None, 'hardware_count': 1},
                       note=None)
    a_dec160 = add_meas(s, lineage='analogalok-4090-dflash2',
                        metric='decode_per_stream', value=42.49, unit='tok/s',
                        context='160k prompt stress, native MTP arm of the same protocol',
                        provenance='forum', date='2026-08-21', source=post2,
                        method_grade='author_report',
                        conditions={'context_label': '160k-prompt stress, native MTP arm',
                                    'workload': None, 'hardware_count': 1})
    a_pre26 = add_meas(s, lineage='analogalok-4090-dflash2',
                       metric='prefill_tok_s', value=2324.0, unit='tok/s',
                       context='26k prompt baseline, native MTP arm (prefill beats DFlash2 here)',
                       provenance='forum', date='2026-08-21', source=post2,
                       method_grade='author_report',
                       conditions={'context_label': '26k prompt baseline, native MTP arm',
                                   'workload': None, 'hardware_count': 1})
    comps = s['evidence']['comparisons']
    comps[0]['a']['measurement_id'] = a_dec26
    comps[0]['b']['measurement_id'] = 'm003'
    comps.append({
        'id': 'dflash2-vs-native-mtp-prefill-26k',
        'question': "What does the builder's stated protocol report for prefill on the same 26k prompt baseline?",
        'candidate_variable': 'speculative_drafter (decode/prefill trade-off, not an isolated variable)',
        'a': {'label': 'native MTP prefill', 'measurement_id': a_pre26},
        'b': {'label': 'DFlash2 prefill', 'measurement_id': 'm005'},
        'result': 'a_better',
        'effect_metric': 'prefill_tok_s',
        'effect_direction': 'increase',
        'contrast_kind': 'uncontrolled',
        'conditions_constant': ['single RTX 4090 24 GB box',
                                'same 26k prompt baseline',
                                'same KV/config as recorded',
                                '--parallel 1'],
        'conditions_unstated': ['same-binary/build equivalence per arm',
                                'sample size / n'],
        'evidence_level': 'c2_observation',
        'lineage_id': 'analogalok-4090-dflash2',
        'independent_reproductions': [],
        'quality_status': 'unchecked',
        'source': post2,
        'locator': 'raw/xsweep_analogalok.json, 2026-08-21 18:50z post',
        'note': 'DFlash2 loses prefill (1,662 vs 2,324) on the same box; a negative recorded for the lane.',
        'date': '2026-08-21',
        'provenance': 'forum',
    })
    # link m003 evidence contrast_id to the C3 comparison too
    byid['m003']['evidence']['contrast_id'] = 'dflash2-vs-native-mtp-decode-26k'
    save(P, s)

# ---------------------------------------------------------------- pilot 03
def pilot_03():
    P = 'qwen38-flash-next-strix-halo-llamacpp-mtp'
    s = load(P)
    s['schema_version'] = 2
    disc = 'https://github.com/ggml-org/llama.cpp/discussions/27950'
    guide = 'https://github.com/drluoto/flash-next-strix-halo'
    branch = 'https://github.com/drluoto/llama.cpp/tree/strix-halo-flash-next'
    s['evidence'] = {
        'rubric_version': '1.0',
        'lineages': [
            {'id': 'drluoto-strix-halo',
             'actor': 'drluoto',
             'publisher': 'drluoto',
             'kind': 'builder_repo',
             'sources': [guide, disc],
             'archive_path': 'directory/tools/history/inputs/pass4-social/raw/gh-discussion_ggml-org_llama.cpp_27950.json',
             'note': 'builder stack + ggml discussion; one lineage.',
            }],
        'claims': [
            {'id': 'native-mtp-on-rocm',
             'technique_id': 'native-mtp',
             'kind': 'mechanism',
             'statement': 'Native multi-token-prediction speculative decoding runs on ROCm through the builder branch with a detached Q8_0 MTP head and the crusaderky detached-head loader fix.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'drluoto-strix-halo',
             'source': guide,
             'locator': 'guide repo build/run section; ggml discussion 27950 body',
             'status': 'recorded'},
            {'id': 'rocm-topk-kernel-fix',
             'technique_id': 'native-mtp',
             'kind': 'configuration',
             'statement': 'The GPU TOP_K lever is a required build-level fix: stock HIP falls back to CPU past ne=1024, so the guide names PR #26592 (hipCUB) or PR #27466 (native radix) as one of three levers.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'drluoto-strix-halo',
             'source': guide,
             'locator': 'guide repo "three levers" section',
             'status': 'recorded'},
        ],
        'comparisons': [{
            'id': 'strix-baseline-vs-full-stack',
            'question': 'How much faster is the full builder stack than the no-speculation baseline on the same 8k file-rewrite workload?',
            'candidate_variable': 'the full branch/kernel/loader/MTP stack (levers were changed together, so the individual lever is not isolated)',
            'a': {'label': 'no-speculation baseline @8k', 'measurement_id': None},
            'b': {'label': 'full stack @8k', 'measurement_id': 'm001'},
            'result': 'b_better',
            'effect_metric': 'decode_per_stream',
            'effect_direction': 'increase',
            'contrast_kind': 'bundle',
            'conditions_constant': [
                'same Strix Halo 128 GB box',
                'same UD-IQ4_XS trunk + Q8_0 MTP sidecar',
                'same 8k file-rewrite workload, greedy, as recorded',
            ],
            'conditions_unstated': [
                'individual lever isolation',
                'same-binary sweep across arms',
                'sample size / n',
                'power/ROCm kernel version drift',
            ],
            'evidence_level': 'c2_observation',
            'lineage_id': 'drluoto-strix-halo',
            'independent_reproductions': [],
            'quality_status': 'unchecked',
            'source': disc,
            'locator': 'ggml discussion 27950 headline/first row',
            'note': 'A bundle contrast: the branch, kernel fix, loader fix and MTP were changed together; individual lever attribution is not established.',
            'date': '2026-08-29',
            'provenance': 'forum',
        }],
        'open_questions': [],
        're_review_triggers': [],
    }
    a23 = add_meas(s, 'drluoto-strix-halo',
                   metric='decode_per_stream', value=16.8, unit='tok/s',
                   context='no-speculation baseline @8k ctx, same UD-IQ4_XS greedy file-rewrite workload',
                   provenance='forum', date='2026-08-29', source=disc,
                   method_grade='author_report',
                   conditions={'context_label': 'no-speculation baseline @8k',
                               'workload': 'file_rewrite', 'greedy': True,
                               'hardware_count': 1, 'spec_decode': None,
                               'max_draft_tokens': None},
                   note='builder-stated baseline in contrast with the recorded 47.1 full stack')
    s['evidence']['comparisons'][0]['a']['measurement_id'] = a23
    # correctness: byte-clean check quoted from the builder
    s['correctness'] = {
        'output_checked': True,
        'checks': [{
            'id': 'byte-clean-long-prompts', 'kind': 'byte_clean',
            'result': 'pass', 'scope': 'file rewrite + new code outputs at 8k/24k context (builder verification)',
            'context_tokens': 8192,
            'measurement_ids': ['m001', 'm002', 'm003', 'm004'],
            'source': guide,
            'locator': 'archived discussion 27950, builder verification note',
            'quote': 'Output verified byte-clean at long prompts — an earlier community MTP port produced genuine-looking tok/s while emitting multilingual noise above ~1k prompt tokens ("read the output, not just the counter").',
            'date': '2026-08-29',
            'lineage_id': 'drluoto-strix-halo',
        }],
        'known_output_failure': None,
        'note': 'Byte-clean verification pertains to the same builder lineage; no independent rerun exists.',
    }
    # known failure: ROCm 10 detached-MTP load failure reported by a commenter
    s['known_failures'] = [{
        'id': 'rocm-10-detached-mtp-load-failure',
        'stage': 'load',
        'trigger': 'newer ROCm (10.0) on the strix-halo-flash-next branch; n_layer_nextn reads 0 despite the KV metadata',
        'effect': "the detached MTP sidecar does not load (tensor blk.0.hc_attn_norm.weight not found); repro broken on newer ROCm as of 2026-09-03",
        'status': 'open',
        'observed_date': '2026-09-03',
        'date': '2026-09-03',
        'lineage_id': 'giulio-volpe-rocm-10-report',
        'source': disc,
        'locator': 'archived discussion 27950 reply, giulio-volpe 2026-09-03',
        'quote': 'n_layer_nextn reads 0 despite the KV metadata; tensor blk.0.hc_attn_norm.weight not found.',
        'resolution': None,
    }]
    s['evidence']['lineages'].append({
        'id': 'giulio-volpe-rocm-10-report',
        'actor': 'giulio-volpe', 'publisher': None,
        'kind': 'community_reply',
        'sources': [disc],
        'locator': 'archived discussion 27950 reply, 2026-09-03',
        'archive_path': 'directory/tools/history/inputs/pass4-social/raw/gh-discussion_ggml-org_llama.cpp_27950.json',
        'note': 'Fail observation (iren-related loader bug); does not reproduce the builder arm itself, so not counted as reproduction.',
    })
    # engine pins (branch/commits), patches, environment
    s['engine']['backend'] = 'rocm'
    s['engine']['fork_revision'] = {
        'repo': 'https://github.com/drluoto/llama.cpp',
        'branch': 'strix-halo-flash-next',
        'commits': ['ea9f94fc7625', '59a40b56ff79'],
        'anchor_date': '2026-08-29',
        'resolution': 'branch_on_anchor',
        'ambiguous': False,
        'source': 'https://github.com/drluoto/llama.cpp/commits/strix-halo-flash-next',
        'locator': 'last branch commits on or before the 2026-08-29 discussion anchor (dated evidence, task #17)',
        'retrieved': '2026-09-16',
        'note': 'later commits (5ad68897a6a5 08-30 long-context fixes; 590ac45bc19b 08-31 GDN rsqrt) post-date the anchor and are deliberately not applied',
    }
    s['engine']['kernel_patches'] = [
        {'id': 'rocm-topk-hipcub', 'pr': '26592',
         'purpose': 'stock HIP falls back to CPU past ne=1024; hipCUB TOP_K keeps cholesky/PFS in talks',
         'source': 'https://github.com/ggml-org/llama.cpp', 'locator': 'ggml PR #26592'},
        {'id': 'topk-native-radix', 'pr': '27466',
         'purpose': 'native radix TOP_K alternative on gfx1151',
         'source': 'https://github.com/ggml-org/llama.cpp', 'locator': 'ggml PR #27466'},
        {'id': 'native-mtp-qwen4exp', 'pr': '27836',
         'purpose': 'native qwen4exp MTP loader on a forked build',
         'source': 'https://github.com/ggml-org/llama.cpp', 'locator': 'ggml PR #27836'},
    ]
    s['engine']['environment'] = {'os': 'Fedora 44', 'rocm': '7.1',
                                  'source': disc,
                                  'locator': 'archived discussion 27950 stack frame',
                                  'date': '2026-08-29'}
    s['run']['repo_revision'] = {
        'commit': 'ec0ad38b4836',
        'anchor_date': '2026-08-29',
        'resolution': 'exact',
        'ambiguous': False,
        'source': disc,
        'locator': 'measured-stack guide commit, same date as the discussion anchor',
        'retrieved': '2026-09-16',
    }
    # conditions/evidence for existing measurements
    evg = {'level': 'c2_observation', 'method_grade': 'author_report',
           'lineage_id': 'drluoto-strix-halo', 'quality_status': 'unchecked',
           'dossier_cited': True}
    rows = {
        'm001': {'context_label': 'file rewrite @8k, full stack', 'spec_decode': 'mtp', 'max_draft_tokens': None, 'workload': 'file_rewrite'},
        'm002': {'context_label': 'new code @8k, full stack', 'spec_decode': 'mtp', 'workload': 'code'},
        'm003': {'context_label': 'file rewrite @24k, full stack', 'spec_decode': 'mtp', 'workload': 'file_rewrite'},
        'm004': {'context_label': 'new code @24k, full stack', 'spec_decode': 'mtp', 'workload': 'code'},
    }
    for mid, cond in rows.items():
        for mm in s['measurements']:
            if mm['id'] == mid:
                mm['conditions'] = {k: v for k, v in dict(cond).items() if v is not None}
                mm['evidence'] = dict(evg, level='c2_observation')
    save(P, s)

# ---------------------------------------------------------------- pilot 04
def pilot_04():
    P = 'qwen38-27b-mlx-8bit-dflash2-atomic-chat-mac256'
    s = load(P)
    s['schema_version'] = 2
    post = 'https://x.com/atomic_chat_hq/status/2090436652363665614'
    card = 'https://huggingface.co/mlx-community/Qwen3.8-27B-8bit'
    s['evidence'] = {
        'rubric_version': '1.0',
        'lineages': [{'id': 'triaddarren-m3-ultra',
                      'actor': 'TriadDarren',
                      'publisher': None,
                      'kind': 'builder_reply',
                      'sources': [post],
                      'locator': 'vendor launch thread, @TriadDarren reply',
                      'archive_path': 'directory/tools/history/inputs/pass4-social/raw/xsweep_atomic_chat_hq.json',
                      'note': 'single reply from a distinct builder; one lineage.'}],
        'claims': [
            {'id': 'atomic-chat-app-dflash2-on-auto',
             'technique_id': 'dflash2-block-diffusion-drafting',
             'kind': 'configuration',
             'statement': 'Runs the Atomic Chat app on Apple Silicon (MLX-VLM backend) with the DFlash2 draft on the Auto setting.',
             'evidence_level': 'c1_configuration',
             'lineage_id': 'triaddarren-m3-ultra',
             'source': post,
             'locator': 'atomic_chat_hq launch-thread reply, archived',
             'status': 'recorded'},
        ],
        'comparisons': [{
            'id': 'baseline-vs-dflash2-auto',
            'question': "What speedup did the builder's own reply record between the Atomic Chat baseline and DFlash2 on Auto on this 256 GB M3 Ultra?",
            'candidate_variable': 'the DFlash2 Auto draft enable toggle',
            'a': {'label': 'baseline, no spec decode', 'measurement_id': 'm001'},
            'b': {'label': 'DFlash2 on Auto', 'measurement_id': 'm002'},
            'result': 'b_better',
            'effect_metric': 'decode_per_stream',
            'effect_direction': 'increase',
            'contrast_kind': 'uncontrolled',
            'conditions_constant': ['same 256 GB M3 Ultra Mac Studio machine as recorded',
                                     'same mlx-community/Qwen3.8-27B-8bit checkpoint'],
            'conditions_unstated': ['context length', 'workload/task', 'sampler/flags',
                                    'sample size / n', 'measured protocol',
                                    'engine/app version'],
            'evidence_level': 'c2_observation',
            'lineage_id': 'triaddarren-m3-ultra',
            'independent_reproductions': [],
            'quality_status': 'unchecked',
            'source': post,
            'locator': 'reply from @TriadDarren inside the vendor launch thread',
            'provenance': 'forum',
            'date': '2026-08-20',
        }],
        'open_questions': [{
            'id': 'm3-ultra-protocol-unstated',
            'question': 'Context length, workload, flags and the measured protocol for the 23 -> 87.6 tok/s run are unstated; the AtomicChat card does not describe it either.',
            'type': 'needs_builder_input',
            'blocks': ['speed_claim', 'exact_reproduction'],
            'owner': 'openkod',
            'status': 'open',
            'source': 'docs/builder-concerns-2026-09-16/builder-questions.md',
            'locator': 'source-lineage / claims section of the M3 Ultra pilot',
        }],
        're_review_triggers': [],
    }
    evg = {'level': 'c2_observation', 'method_grade': 'author_report',
           'lineage_id': 'triaddarren-m3-ultra', 'quality_status': 'unchecked',
           'dossier_cited': True}
    for mm in s['measurements']:
        mm['evidence'] = dict(evg)
        if mm['id'] == 'm001':
            mm['conditions'] = {'context_label': 'baseline, no speculative decoding',
                                'workload': None, 'hardware_count': 1}
    save(P, s)


if __name__ == '__main__':
    for fn in (pilot_01, pilot_02, pilot_03, pilot_04):
        print(fn.__name__)
        fn()
