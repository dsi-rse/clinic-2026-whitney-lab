# OpenRouter provider comparison

Made by `experiments/openrouter_providers/compare_providers.py` from 9 run folders; see `provenance.json` for the commits and the run folders.

- `arms.csv`: one row per provider arm.
- `per_patient.csv`: each arm's answer in every repeat, and the cluster's 20-repeat tally (old task contract, a reference only).
- `summary.csv`: patients whose most common answer is the same in every arm that answered, and how many of those match the cluster's most common answer.
- `prices.csv`: the prices `cost_usd` uses.

Remake with the command in `experiments/openrouter_providers/README.md`, passing `--prices` this folder's `prices.csv`; the tables then match exactly.
