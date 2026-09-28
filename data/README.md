# Synthetic data

No generated datasets are tracked. Run:

```powershell
python data_generators\generate_all.py --output data\generated
```

The deterministic generator uses seed `20260927`, emits fictional basketball,
football, soccer, and hockey data, and writes:

- `static/fan_profile.csv`
- `static/game_context.csv`
- `static/promotion_history.csv`
- `streaming/fan_engagement_events.jsonl`
- `streaming/pos_transactions.jsonl`
- `streaming/game_excitement_index.jsonl`
- `manifest.json`

`scripts/fabric_bootstrap.py` uploads these files to OneLake, loads the CSV
tables into the Lakehouse, and ingests the JSONL files into Eventhouse.
