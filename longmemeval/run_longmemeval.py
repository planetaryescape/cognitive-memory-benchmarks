#!/usr/bin/env python3
"""
Entry point for running LongMemEval (ICLR 2025) evaluation.

TODO: Implement once LongMemEval dataset is downloaded.
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description="Run LongMemEval evaluation with cognitive-memory")
    parser.add_argument("--config", type=str, help="Run config: apples-to-apples | benchmark-pure | best-tuned")
    parser.add_argument("--data", type=str, help="Path to LongMemEval JSONL file")
    args = parser.parse_args()

    raise NotImplementedError(
        "LongMemEval integration not yet implemented. "
        "See longmemeval/README.md for the integration plan."
    )


if __name__ == "__main__":
    main()
