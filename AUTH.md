# CDP Auth Setup (Local Testing)

This project uses `cdp.auth.get_auth_headers()` from the Coinbase CDP Python SDK to
sign each request with a short-lived JWT. The SDK is **required** for authenticated
requests to succeed.

## 1) Install the CDP SDK

Follow the official CDP Python SDK installation steps from Coinbase. Once installed,
`python -c "from cdp import auth"` should succeed.

## 2) Provide Credentials

The CDP SDK reads credentials from environment variables (per its documentation).
Set the required variables before running the pipeline:

```bash
export CDP_API_KEY_ID="<your-key-id>"
export CDP_API_PRIVATE_KEY="<your-private-key>"
```

> **Note:** The exact variable names are defined by the CDP SDK. If your SDK
> version uses different names, update them accordingly.

## 3) Validate Auth Locally

```bash
python - <<'PY'
from cdp import auth

headers = auth.get_auth_headers(
    method="GET",
    host="api.cdp.coinbase.com",
    path="/platform/v2/evm/swaps/quote",
)
print(headers)
PY
```

If you see an `Authorization: Bearer ...` header, credentials are wired correctly.
