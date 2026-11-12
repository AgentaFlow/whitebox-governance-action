# WhiteBoxXAI Governance Action

Gate a model deployment on your organization's [WhiteBoxXAI](https://whiteboxxai.com) policy.

The Action does two things:

1. It sends your repository's `whitebox.yaml` to WhiteBoxXAI.
2. It evaluates a model against that policy: its latest drift report and its latest bias audit.

The job fails when the result is `block`. Each violation shows up as an annotation on the run, and the
result is also available as step outputs.

Full guide, including how the policy is evaluated:
[Policy-as-Code & GitOps](https://docs.whiteboxxai.com/integrations/policy-as-code/).

## Usage

```yaml
# .github/workflows/governance.yml
name: Model governance
on:
  push:
    branches: [main]
  pull_request:

jobs:
  policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: AgentaFlow/whitebox-governance-action@v1
        with:
          api_key: ${{ secrets.WHITEBOX_API_KEY }}
          model_id: ${{ vars.WHITEBOX_MODEL_ID }}
          # Sync only on main, so a pull request can't change the policy in force.
          sync: ${{ github.event_name == 'push' }}
```

The policy file:

```yaml
# whitebox.yaml
minor_drift_action: warn      # when the model's latest drift report detected drift
major_bias_action: block      # when the model's latest bias audit detected bias
auto_approve_minor: false
```

Each action must be `warn` or `block`. Any other value makes the sync fail with HTTP 422, and the step
fails with it.

## Inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `api_key` | yes | | A WhiteBoxXAI API key. Store it as a repository secret. |
| `policy_file` | no | `whitebox.yaml` | Path to the policy file. |
| `sync` | no | `true` | Sync the policy file before evaluating. |
| `model_id` | no | | The model to evaluate. Leave it empty to sync only. |
| `base_url` | no | `WHITEBOX_BASE_URL`, then `https://api.whiteboxxai.com` | The API address. On Business Cloud, set it to your tenant's API address. |

## Outputs

| Output | Description |
| --- | --- |
| `action` | `pass`, `warn` or `block` |
| `allowed` | `false` only when `action` is `block` |
| `violations` | JSON array of `{policy_rule, action, detail}` |

The outputs are empty when no model is evaluated. To fail on a warning as well as a block:

```yaml
      - uses: AgentaFlow/whitebox-governance-action@v1
        id: policy
        with:
          api_key: ${{ secrets.WHITEBOX_API_KEY }}
          model_id: ${{ vars.WHITEBOX_MODEL_ID }}
      - if: steps.policy.outputs.action == 'warn'
        run: exit 1
```

## Notes

- This is a Docker container action, so it runs on Linux runners only.
- The evaluation uses the model's latest drift report and latest bias audit. It doesn't create either one.
  To have the decision cover the build you're deploying, run those steps earlier in the pipeline.
- The step also fails on any HTTP error from the API, such as a bad key, an unknown model or an invalid
  policy file. The error is printed in the log.

## License

[MIT](LICENSE)
