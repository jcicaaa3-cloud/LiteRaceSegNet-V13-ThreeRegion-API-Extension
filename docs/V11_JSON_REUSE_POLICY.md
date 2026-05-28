# v11 JSON Reuse Policy

## Keep from v11

Reusable as legacy integration reference:

- request id convention,
- status/error code shape,
- mask/overlay/evidence file path fields,
- batch-service idea,
- backend-to-model-server flow.

## Do not keep from v11

Do not reuse these in the V13 API package:

- old model structure description,
- old checkpoint path as final path,
- old metrics,
- outdated screenshots or README claims,
- ambiguous class mapping,
- demo/fallback behavior as evidence.

## Recommended wording

```text
v11 is used only as a legacy reference for JSON schema and backend integration flow.
Actual inference, checkpoint, config, class mapping, metrics, and result interpretation are based on LiteRaceSegNet V13.
```
