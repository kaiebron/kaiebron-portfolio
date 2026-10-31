# kaiebron.com

Portfolio site plus a small serverless backend.

```
EventBridge (every 30 min) -> Lambda (Python) -> Open-Meteo API
                                   |
                                   v
                        S3 bucket: data/weather.json
                                   |
                     CloudFront -> site (site/app.js renders it)
```

- `site/` static frontend (CSS-only typewriter name, live weather card)
- `backend/app.py` Lambda that fetches the forecast and writes `data/weather.json`
- `template.yaml` AWS SAM template: Lambda, EventBridge schedule, IAM, log group
- `.github/workflows/deploy.yml` test, deploy backend, sync site, invalidate cache
- `tests/` pytest unit tests (`pip install pytest && pytest`)

`site/data/weather.json` is sample data for local preview only. The workflow
excludes `data/*` from `s3 sync`, so the Lambda's real file is never overwritten or deleted.

## One-time AWS setup (GitHub OIDC, no stored keys)

1. IAM -> Identity providers -> Add provider: OpenID Connect,
   URL `https://token.actions.githubusercontent.com`, audience `sts.amazonaws.com`.
2. IAM -> Roles -> Create role (Web identity, the provider above) named `github-portfolio-deploy`.
   Use this trust policy (replace ACCOUNT_ID and OWNER/REPO):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"},
       "Action": "sts:AssumeRoleWithWebIdentity",
       "Condition": {
         "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
         "StringLike": {"token.actions.githubusercontent.com:sub": "repo:OWNER/REPO:ref:refs/heads/main"}
       }
     }]
   }
   ```
3. Permissions for the role: CloudFormation, Lambda, EventBridge/Events, Logs, S3 (SAM's
   artifact bucket and your site bucket), IAM role create/pass for the stack, and
   `cloudfront:CreateInvalidation`. Start broad to get it working, then tighten.

## GitHub repo settings

Settings -> Secrets and variables -> Actions:

| Type | Name | Value |
|---|---|---|
| Secret | `AWS_ROLE_ARN` | ARN of `github-portfolio-deploy` |
| Variable | `AWS_REGION` | Region of your S3 bucket (your console was on us-east-2) |
| Variable | `S3_BUCKET` | Exact site bucket name |
| Variable | `CLOUDFRONT_DISTRIBUTION_ID` | `E2TNS2J29D0H74` |

Push to `main` and the pipeline runs. To change the city, edit the `Latitude`,
`Longitude`, and `LocationLabel` defaults in `template.yaml`.

## Before you ship

- Replace `YOUR_EMAIL@example.com` in `site/index.html`
- Add `site/resume.pdf` and a portrait (`site/portrait.jpg`, then swap the placeholder in the hero)
- Review the copy in About, Projects, and Experience
