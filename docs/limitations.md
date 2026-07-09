# Limitations

- Transcript quality is a hard dependency. Poor ASR can reduce or block the usable editing scope.
- Current Chinese ASR Recovery cannot reliably fix some classroom videos automatically.
- Avoiding risky transcript regions can sacrifice storyline completeness.
- Task Coverage Gate prevents degenerate outputs, but it is still a structured proxy, not a human editor.
- LLM Judge scores can fluctuate and must not be treated as human evaluation.
- A first-cut review video is not a publish-ready final edit.
- Multi-agent repair increases latency and API cost.
- Success cases are limited.
- The project does not prove the selector is better than traditional methods on public benchmarks.
- OCR and multiple ASR backends are extension points, not solved guarantees.
- Human review remains necessary before any production use.
