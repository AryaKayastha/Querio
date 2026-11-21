# 06 — Deployment plan: Google Cloud on a free-tier account

**Status:** draft for team review · written 2026-11-21 · prices, limits and terms checked on Google's pages the same day. Most of those pages show no "last updated" date, so re-check the numbers marked ⚠ before go-live.

**Read this if you are:** setting up the cloud project, preparing the code for deployment, or deciding whether Querio can use Gemini through Google Cloud.

---

## 1. Summary

**Recommended setup (about $0 a month for demos):**

| Part | Where it runs | Cost |
|---|---|---|
| Frontend (React build) | Firebase Hosting, Spark plan | Free |
| Backend (FastAPI) | Cloud Run, public, region `asia-south1` (Mumbai) | Inside Cloud Run's free tier |
| Chatbot (FastAPI + LangChain) | Cloud Run, **private** (only the backend can call it), Chroma index baked into the image | Inside Cloud Run's free tier |
| Postgres (query log) | **Neon Free** (managed Postgres; outside Google Cloud) | Free |
| Secrets | Secret Manager (3 secrets) | Free |
| AI models | **Gemini Developer API** (our current API key) with Groq as fallback | Free tier for demos; about $5–20/month on the paid tier for a student pilot |

**Can we use Gemini *through GCP* (Vertex AI)?** Technically yes, but it is **not free on a new account**, so we shouldn't. Vertex AI has no free tier. Since **2026-11-16**, Google's $300 trial credit no longer pays for Vertex AI on new sign-ups. Keep calling Gemini with the AI Studio API key from inside Cloud Run. Section 2 has the details.

**Two things to settle before going live:**
1. **Paid Gemini for real students.** On Gemini's free tier, Google uses what users type to improve its products, and human reviewers may read it. That's fine for a mentor demo but not for real student questions, so plan $5–10 of prepaid Gemini credit for the pilot.
2. **Age restriction in Google's terms.** Google's generative-AI terms forbid apps "directed towards or likely to be accessed by individuals under the age of 18". The mentor or college needs to confirm Querio's users are 18+, or that access is limited to them (section 9).

---

## 2. Can we use Gemini through Google Cloud?

There are three ways to call Gemini from a Cloud Run service:

| Route | How it authenticates | Free tier? | Does the $300 trial credit pay for it? | Works for Querio? |
|---|---|---|---|---|
| **A. Gemini Developer API** (AI Studio key, what we use today) | API key, stored in Secret Manager | **Yes**, rate-limited ⚠ | **No** ("can't pay for Gemini API in AI Studio costs") | ✅ **Recommended** |
| **B. Vertex AI** (Google has renamed it "Gemini platform") | Cloud Run service account, no API key | **No**, pay-as-you-go only | **No** for accounts that sign up or upgrade **on or after 2026-11-16** | Technically ✅, but costs money from day one |
| **C. Vertex AI Express mode** | API key | 90 days free for brand-new Gmail users only | n/a | ❌ Pre-GA, and it has **no embeddings API**, so retrieval can't work |

**Why route B is technically ready (if the college pays later):**
- The installed `langchain-google-genai` 4.3.4 supports Vertex AI. Set `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION=global`, remove the API key, and give the chatbot's service account the Vertex AI User role.
- Vertex serves the same models at the same token prices, including `gemini-embedding-2`, the model our Chroma index was built with. So the index very likely doesn't need re-embedding. Confirm with the cosine check `ingest.py` already does (`SAME_MODEL_MIN_COSINE`) before switching.
- So switching later is a configuration change, not a rewrite.

**Exception to check.** If our Google Cloud account signed up for its trial **before 2026-11-16** and hasn't upgraded, the credit *may* still cover Vertex until the trial ends. Google's wording suggests that upgrading the account, which we must do by day 90 to stay online (section 8), would end that. Check in Console › Billing before relying on it.

### Free vs paid Gemini (route A)

| | Free tier | Paid tier (link billing; **prepay**, minimum $5) |
|---|---|---|
| Rate limits | Low, and visible only on our project's AI Studio rate-limit page ⚠. Reports range from about 20 to about 500 requests/day per model; we have hit the daily cap in testing | Much higher (Tier 1) |
| What Google does with prompts | **Uses them to improve its products; human reviewers may read them.** Google's terms say not to submit personal information | **Not used for training**; logged briefly for abuse detection only |
| Suitable for | Development, mentor demos | A pilot with real students |

### Which model, and what it costs

`gemini-flash-lite-latest` (our current setting) resolves to **`gemini-3.5-flash-lite`**; checked with a live call on 2026-11-21. An alias can move to a different model at any time, so **pin an explicit model ID** in production.

| Model | Price per 1M tokens (input / output) ⚠ | Cost at 300 questions/day* |
|---|---|---|
| `gemini-3.5-flash-lite` (what we use and tested with) | $0.30 / $2.50 | about $19/month |
| `gemini-3.1-flash-lite` (older, cheaper) | $0.25 / $1.50 | about $13.50/month |
| `gemini-embedding-2` (question embeddings) | $0.20 | about $0.05/month |

\* 9,000 questions/month at about 3,000 input + 500 output tokens each (two model calls per question). At 50 questions/day, 3.5 Flash-Lite costs about $3/month.

Pin `gemini-3.5-flash-lite` to keep today's tested behaviour. Switch to `gemini-3.1-flash-lite` only if `routing_accuracy` and `golden_qa` still pass on it.

---

## 3. Target architecture

```text
 Student's browser
      │ HTTPS
      ▼
 Firebase Hosting  ── serves the React build from a global CDN                 (free: Spark plan)
      │ POST https://querio-backend-<hash>.a.run.app/chat
      ▼
 Cloud Run: querio-backend   public · asia-south1 · max 1 instance               (free tier)
      │   ├─ writes query_log ─────────────► Neon Free Postgres (AWS, Singapore)
      │   └─ calls the chatbot with a Google ID token (IAM role run.invoker)
      ▼
 Cloud Run: querio-chatbot   private · asia-south1 · max 2 instances             (free tier)
      │   Chroma index (29 MB, read-only) copied into the container image
      ├─► Gemini Developer API   chat (routing + answers) and question embeddings
      └─► Groq API               chat fallback when Gemini fails

 Supporting services: Secret Manager (API keys, DB URL) · Cloud Build · Artifact Registry
```

| Choice | Why | Rejected alternatives |
|---|---|---|
| **Cloud Run** for both Python services | Scales to zero, so idle time costs nothing. Its free tier covers our expected load. HTTPS and logs come built in | One e2-micro VM running everything (`02_architecture.md` assumed this): 1 GB RAM is tight for the chatbot, the free VM exists only in US regions, and its public IP costs about $3.65/month ⚠ |
| **`asia-south1` (Mumbai)** | Closest region to CHARUSAT. It's in Cloud Run's cheapest price tier, so the free tier counts in full ⚠ | `us-central1`: needed only if we used the free e2-micro or free Cloud Storage, which this plan doesn't |
| **Chatbot private** (no public access) | Only the backend can call it, so nobody can spend our model quota by calling the chatbot directly. Service-to-service calls in one region are free, and no VPC is needed | Internal-only ingress: needs VPC routing |
| **Chroma index inside the image** | It's 29 MB and read-only at runtime. Image size doesn't slow startup or count against memory | Mounting it from Cloud Storage: Chroma uses SQLite, and Google advises against databases on Cloud Storage mounts |
| **Neon Free** for Postgres | Managed, free with no card, doesn't pause for inactivity, and connects over the internet (no VPC) | **Cloud SQL**: no free tier; its trial instance is deleted after 30 days. **Supabase Free**: pauses after a week idle. **Postgres on the e2-micro**: we'd own backups and patching, it's US-only, and it costs about $3.65/month for its IP ⚠ |
| **Firebase Hosting** for the frontend | Free CDN with HTTPS, single-page-app routing, one-command deploy | Cloud Storage website: no HTTPS on a custom domain without a paid load balancer. Cloud Run + nginx: works, but adds cold starts |

---

## 4. Free-tier fit and monthly cost

Assumes a pilot of **300 questions/day** (9,000/month), with each question keeping a Cloud Run instance busy for about 8 s.

| Service | Free allowance per month ⚠ | Our estimated use | Cost |
|---|---|---|---|
| Cloud Run: requests | 2,000,000 | about 20,000 | $0 |
| Cloud Run: CPU | 180,000 vCPU-seconds | about 144,000 (worst case, both services, no overlap) | $0. Going over costs about $0.24 per extra 10,000 vCPU-s |
| Cloud Run: memory | 360,000 GiB-seconds | about 108,000 | $0 |
| Firebase Hosting | 10 GB storage, 360 MB/day transfer | about 1 MB build; about 125 KB per page load | $0 |
| Neon Postgres | 1 GB storage, 100 compute-hours/project | under 50 MB | $0 |
| Secret Manager | 6 secret versions, 10,000 accesses | 3 versions | $0 |
| Cloud Build | 2,500 build-minutes | a few minutes per deploy | $0 |
| Artifact Registry | 0.5 GB | the chatbot image will likely exceed this | about $0.05–0.15 (keep only the last 2 images) |
| Outbound data | small | answers are about 5 KB each | under $0.01 |
| **Gemini** | free tier (rate-limited, prompts used for training) | about 600 chat calls + 300 embedding calls/day | $0 on the free tier, **about $13–19 on the paid tier** |
| **Groq** (fallback) | free tier: 200,000 tokens/day on `gpt-oss-120b` | only when Gemini fails | $0 |

**Totals:**
- **Demo setup:** about $0/month (free Gemini).
- **Student pilot:** about $15–20/month, almost all of it Gemini. Prepay $5–10 at a time; the Gemini API stops (HTTP 402) when the prepaid balance reaches zero.
- **Budget alert:** set one at $5 so any surprise shows up early.

---

## 5. Decisions needed from the team

| # | Decision | Recommendation | Who |
|---|---|---|---|
| D1 | Whose Google account and billing account hosts Querio, and when was it created? | A college-owned account if possible. A team member's account works, but billing must be upgraded by trial day 90 (section 8). The creation date decides the Vertex credit question in section 2 | Team + mentor |
| D2 | Free or paid Gemini for the pilot? | Free for demos; **paid (prepay $5–10) before real students use it** | Team + mentor |
| D3 | Can we confirm users are 18+ (Google's age term)? | Ask the mentor/college. If not, Querio can't be offered publicly on Gemini (section 9) | Mentor |
| D4 | Database: Neon or Postgres on a VM? | Neon | Backend lane |
| D5 | Is losing chat history after about 15 minutes idle acceptable for the pilot? | Yes for now (section 6, item 4); store it in Postgres later if needed | Team |
| D6 | Custom domain, or Firebase's default `<project>.web.app`? | Default for the pilot | Frontend lane |

---

## 6. Code changes before the first deploy

None of these exist yet. Do them on a branch and merge through a PR before running the steps in section 7.

| # | Change | Why | Lane |
|---|---|---|---|
| 1 | **Make CORS origins configurable**: read `ALLOWED_ORIGINS` from the environment, keeping today's localhost ports as the default | `bridge.py` only allows `localhost:5173–5177`, so the deployed frontend's requests would be blocked | Backend |
| 2 | **Call the chatbot with a Google ID token** when `CHATBOT_AUTH=google`, using `google-auth`'s `id_token.fetch_id_token(..., audience=CHATBOT_API_URL)`, cached until expiry | The chatbot will be private; Cloud Run rejects calls without a valid token | Backend |
| 3 | **Per-user rate limit on `/chat`**, e.g. 10 questions/minute per IP (Cloud Run passes the client IP in `X-Forwarded-For`) | Once public, one person or script could burn the whole Gemini quota or budget. Left out of QRO-02 | Backend |
| 4 | **Accept in-memory chat history for the pilot** and deploy the backend with `max-instances=1` | History lives in the backend's memory (`InMemorySessionStore`). With one instance it survives while the instance is warm, but resets after about 15 minutes idle. Moving it into Postgres is the follow-up if D5 says no | Backend |
| 5 | **Chatbot container**: `chatbot/Dockerfile`, `chatbot/.gcloudignore` and a runtime-only `requirements.runtime.txt` | **(a)** `chatbot/vectorstore/` is gitignored, and `gcloud run deploy --source` uses `.gitignore` when there's no `.gcloudignore`, so the index would be silently left out. **(b)** Run with `PYTHONPATH=/app/src` (copy `src/` and `vectorstore/` into `/app`) and don't `pip install` the package: `config.py` finds the index relative to its own file. **(c)** Leave out `ragas`, `pytest`, `pymupdf`, `openpyxl` and `pypdf`, which only evaluation, tests and ingestion use. Today's virtualenv is 946 MB | Chatbot |
| 6 | **Pin the model**: `GEMINI_CHAT_MODEL=gemini-3.5-flash-lite` in production | So a change to the alias can't silently change answers or price | Chatbot |
| 7 | **Backend container**: `backend/Dockerfile` + `.gcloudignore`. Run Alembic migrations **once from a laptop** against Neon, not at container start | Several instances running migrations at startup can race | Backend |
| 8 | **Frontend production build**: set `VITE_API_BASE_URL` to the backend's Cloud Run URL at build time; add `firebase.json` with a single-page-app rewrite to `index.html`; add a one-line notice under the chat box ("Don't share personal information such as roll numbers or phone numbers") | The API URL is baked in at build time; the notice protects students on any Gemini tier | Frontend |
| 9 | **Use separate API keys** (separate Google/Groq projects) for development and for the deployed app | On 2026-11-21 a day of test runs used up Groq's daily token budget. Separate keys keep testing from taking the live app down | Everyone |

---

## 7. Deployment runbook

Commands are for the `gcloud` CLI (Google Cloud SDK) and `firebase-tools`. Replace `PROJECT_ID` and the URLs. Run them from the repo root unless a step says otherwise.

### Phase 0 — Project, billing, budget (once)

```bash
gcloud projects create PROJECT_ID --name="Querio"
gcloud config set project PROJECT_ID
gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
gcloud config set run/region asia-south1
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
    artifactregistry.googleapis.com secretmanager.googleapis.com
```

- In **Console › Billing › Budgets & alerts**, create a budget of **$5** (or ₹ equivalent) with alerts at 50%, 90% and 100%. A budget only alerts; it doesn't stop spending.
- Note the trial end date (90 days from sign-up) in the team calendar.

### Phase 1 — Code changes

Merge the section 6 changes. Then check that the chatbot image builds and answers locally:

```bash
docker build -t querio-chatbot chatbot
docker run --rm -p 8001:8080 --env-file chatbot/.env querio-chatbot
curl -s localhost:8001/health
```

The port mapping assumes the Dockerfile's CMD listens on `$PORT` (Cloud Run sets it, default 8080).

### Phase 2 — Database (Neon)

1. Create a free Neon project in the **AWS Singapore** region (`aws-ap-southeast-1`; check it's in Neon's region list), with database `querio`.
2. Copy the connection string and convert it to SQLAlchemy form, keeping SSL:
   `postgresql+psycopg://USER:PASSWORD@HOST/querio?sslmode=require`
3. Create the tables from a laptop:

```bash
cd backend
DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/querio?sslmode=require" \
    .venv/Scripts/python.exe -m alembic upgrade head
```

### Phase 3 — Service accounts and secrets

```bash
gcloud iam service-accounts create querio-chatbot --display-name="Querio chatbot"
gcloud iam service-accounts create querio-backend --display-name="Querio backend"

printf '%s' "GEMINI_KEY"   | gcloud secrets create gemini-api-key --data-file=-
printf '%s' "GROQ_KEY"     | gcloud secrets create groq-api-key   --data-file=-
printf '%s' "DATABASE_URL" | gcloud secrets create database-url   --data-file=-

for s in gemini-api-key groq-api-key; do
  gcloud secrets add-iam-policy-binding $s --role=roles/secretmanager.secretAccessor \
    --member=serviceAccount:querio-chatbot@PROJECT_ID.iam.gserviceaccount.com
done
gcloud secrets add-iam-policy-binding database-url --role=roles/secretmanager.secretAccessor \
  --member=serviceAccount:querio-backend@PROJECT_ID.iam.gserviceaccount.com
```

Each secret update adds a version. Destroy old versions so the project stays within the 6 free active versions.

### Phase 4 — Deploy the chatbot (private)

Re-run ingestion locally first if any documents changed, so the image carries the current index.

```bash
gcloud run deploy querio-chatbot --source chatbot \
  --no-allow-unauthenticated \
  --service-account=querio-chatbot@PROJECT_ID.iam.gserviceaccount.com \
  --cpu=1 --memory=1Gi --concurrency=8 --min-instances=0 --max-instances=2 \
  --cpu-boost --timeout=60 \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest,GROQ_API_KEY=groq-api-key:latest \
  --set-env-vars=GEMINI_CHAT_MODEL=gemini-3.5-flash-lite,CHAT_DEADLINE_SECONDS=40,MAX_CONCURRENT_CHATS=4
```

- `--concurrency=8` with `MAX_CONCURRENT_CHATS=4`: up to 4 questions are answered at once and up to 4 more wait inside the 40 s deadline. Beyond that, Cloud Run starts the second instance.
- Start at 1 GiB of memory. If the chatbot's memory graph runs near the limit or the instance restarts during testing, raise it to 2 GiB.

### Phase 5 — Deploy the backend (public)

```bash
gcloud run services add-iam-policy-binding querio-chatbot --role=roles/run.invoker \
  --member=serviceAccount:querio-backend@PROJECT_ID.iam.gserviceaccount.com

gcloud run deploy querio-backend --source backend \
  --allow-unauthenticated \
  --service-account=querio-backend@PROJECT_ID.iam.gserviceaccount.com \
  --cpu=1 --memory=512Mi --concurrency=20 --min-instances=0 --max-instances=1 \
  --cpu-boost --timeout=60 \
  --set-secrets=DATABASE_URL=database-url:latest \
  --env-vars-file=backend/deploy.env.yaml
```

`backend/deploy.env.yaml` is a new file. Use a file because `ALLOWED_ORIGINS` contains characters that `--set-env-vars` handles badly:

```yaml
CHATBOT_API_URL: "https://querio-chatbot-HASH.asia-south1.run.app"
CHATBOT_AUTH: "google"
CHATBOT_TIMEOUT_SECONDS: "45"
ALLOWED_ORIGINS: "https://PROJECT_ID.web.app,https://PROJECT_ID.firebaseapp.com"
```

### Phase 6 — Deploy the frontend (Firebase Hosting)

```bash
npm install -g firebase-tools
firebase login
firebase projects:addfirebase PROJECT_ID
cd frontend
VITE_API_BASE_URL="https://querio-backend-HASH.asia-south1.run.app" npm run build
firebase init hosting      # public directory: dist · single-page app: yes · don't overwrite index.html
firebase deploy --only hosting
```

### Phase 7 — Verify before sharing the link

- [ ] Backend `/health` returns `{"status":"ok","chatbot":"ok"}`.
- [ ] The chatbot URL returns 403 when called directly without a token (it's private).
- [ ] `/docs` returns 404 on both services (`ENABLE_API_DOCS` is unset).
- [ ] Re-run the post-merge smoke checks (QRO-01, 03, 04, 05, 08, 10, 11, 15, 16) against the deployed backend.
- [ ] Re-run the QRO-02 load test (6 users × 3 rounds): no raw 500s, and every failure is a 503 with `Retry-After`.
- [ ] A question appears in Neon's `query_log`.
- [ ] The first question after 15+ minutes idle answers within the 45 s timeout. This is the cold-start case: the chatbot loads LangChain/Chroma and builds its keyword index on first use.
- [ ] The budget alert email arrives (send a test from the Billing console).

---

## 8. Running it after launch

| Task | How |
|---|---|
| **Update documents** | Add or replace files under `data/`, run `python -m querio_chatbot.ingestion.ingest <DOMAIN>` locally, then redeploy the chatbot (Phase 4). The new index ships in the new image |
| **Watch errors** | `gcloud run services logs read querio-chatbot --limit=50`. Look for `falling back to groq` and `replying 503`, which mean the models are failing or out of quota |
| **See what students ask** | Query `query_log` in Neon's SQL editor (same query as in the `run-querio` skill) |
| **Watch spending** | Budget alerts, plus the AI Studio usage page for Gemini |
| **Trial end, day 90 (critical)** | The free trial account **closes** at day 90 or when the $300 is spent, whichever comes first; services stop, and data is deleted after 30 days. **Upgrade to a paid billing account before day 90.** After upgrading, the Always Free allowances still apply, so the setup above still costs about $0 plus Gemini |
| **Clean up images** | Artifact Registry › repository `cloud-run-source-deploy` › cleanup policy: keep the 2 most recent versions per image |

---

## 9. Risks and unverified points

| Risk | Impact | Mitigation |
|---|---|---|
| **Google's under-18 term.** Service Specific Terms §20(d) prohibits generative-AI use in apps "directed towards or likely to be accessed by" under-18s. Applies to both the Gemini API and Vertex. The section number and wording come from a page summary; confirm on https://cloud.google.com/terms/service-terms | Using Gemini for Querio could breach Google's terms | Mentor/college confirms users are 18+, or access is restricted to enrolled 18+ students. Groq's terms haven't been checked |
| Gemini free-tier quota is small and its exact limits aren't published | Demos fail with "Querio is busy" (the QRO-02 503) | Paid tier for the pilot; separate dev and prod keys (section 6, item 9) |
| Cold start of the chatbot after idle | The first question after idle is slow and could near the 45 s timeout | `--cpu-boost`; measure in Phase 7. If it's too slow, `min-instances=1` on the chatbot costs about $13/month (estimated, not measured) |
| Chat history resets after idle | A follow-up question after a pause loses its context | Accepted for the pilot (D5); persist history in Postgres later |
| Neon is outside Google Cloud | About 60 ms per query-log write; Neon wakes from idle on the first write | Logging failures never break a chat (the backend already swallows them); the 2 s connect timeout bounds the wait |
| Free-tier numbers drift ⚠ | Costs differ from section 4 | Budget alert at $5; re-check the source pages before go-live |
| Vertex embeddings might not exactly match the Developer API's (unverified) | Only matters if we switch to route B | Run the `ingest.py` cosine check before switching; re-embedding all 950 chunks costs cents if needed |

---

## 10. Sources (checked 2026-11-21)

- Google Cloud free tier and trial terms: https://docs.cloud.google.com/free/docs/free-cloud-features
- Cloud Run pricing and regions: https://cloud.google.com/run/pricing
- Cloud Run service-to-service auth: https://docs.cloud.google.com/run/docs/authenticating/service-to-service
- Cloud Run image size and startup: https://docs.cloud.google.com/run/docs/tips/general
- Cloud Storage volume mounts (why not for Chroma): https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
- Cloud SQL free trial instance: https://docs.cloud.google.com/sql/docs/postgres/free-trial-instance
- Vertex AI / Gemini platform pricing: https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
- Vertex AI Express mode: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/express-mode/overview
- `gemini-embedding-2` on Vertex: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/embedding-2
- Gemini API pricing, billing tiers, rate limits, terms: https://aistudio.google.com/docs/pricing · https://aistudio.google.com/docs/billing · https://aistudio.google.com/docs/rate-limits · https://aistudio.google.com/docs/terms
- Google Cloud Service Specific Terms (age restriction): https://cloud.google.com/terms/service-terms
- Firebase pricing: https://firebase.google.com/pricing
- Neon pricing and regions: https://neon.com/pricing · https://neon.com/docs/introduction/regions
- LangChain Google GenAI (Vertex backend): https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai
