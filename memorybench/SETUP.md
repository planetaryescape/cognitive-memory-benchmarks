# MemoryBench Setup Guide

## Requirements
- Linux with NVIDIA GPU (vLLM doesn't run on macOS)
- ~40GB GPU VRAM for Qwen3-8B + embedding model
- Python 3.10+

## Quick Start (Standalone Mode - macOS compatible)

Uses OpenAI API instead of vLLM. Good for initial testing.

```bash
cd cognitive-memory-benchmarks
pip install datasets  # for HuggingFace download
source .venv/bin/activate

python memorybench/run_memorybench.py --standalone \
    --datasets Locomo-0 Locomo-1 Locomo-2 \
    --deep-recall --rerank \
    --output memorybench/results/
```

## Full Protocol (Linux + vLLM)

### 1. Start vLLM servers

```bash
# Main LLM (Qwen3-8B)
vllm serve Qwen/Qwen3-8B \
    --port 12366 \
    --tensor-parallel-size 1 \
    --gpu-memory-utilization 0.7

# Embedding model
vllm serve Qwen/Qwen3-Embedding-0.6B \
    --port 12377 \
    --task embedding

# Judge model (for WritingBench datasets only)
vllm serve AQuarterMile/WritingBench-Critic-Model-Qwen-7B \
    --port 12388
```

### 2. Register our solver in the framework

```bash
cd memorybench/repo

# Copy solver files
cp ../solver.py src/solver/cognitive_memory.py
# Register in factory (add to src/solver/__init__.py)
```

### 3. Add config

Create `configs/memory_systems/cognitive_memory.json`:

```json
{
    "llm_provider": "vllm",
    "llm_config": {
        "model": "Qwen/Qwen3-8B",
        "vllm_base_url": "http://localhost:12366/v1",
        "temperature": 0.1
    },
    "retrieve_k": 20,
    "deep_recall": true,
    "rerank": true,
    "rerank_factor": 2
}
```

### 4. Run evaluation

```bash
python -m src.predict \
    --memory_system cognitive_memory \
    --domain Open-Domain \
    --dataset_config configs/datasets/domain.json

python -m src.evaluate --result_path off-policy/results/
python -m src.single_summary --result_path off-policy/results/
```

## Datasets

MemoryBench has 27 datasets across 3 domains:
- **Open-Domain**: Locomo-0..9, DialSim (3 shows), HelloBench, WritingPrompts, WritingBench, NFCats
- **Legal**: JuDGE, LexEval (3 tasks), WritingBench-Law
- **Academic**: HelloBench-QA, HelloBench-Writing, IdeaBench, JRE-L, LimitGen, WritingBench-Academic

For our paper, Locomo-0..9 are most relevant (same data as our LoCoMo benchmark).
