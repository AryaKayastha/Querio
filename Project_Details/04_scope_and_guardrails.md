# Querio — Scope & Guardrails

**Read this before designing or building any feature that touches Domain 4 (Career/Internship/Placement, incl. NOC) or Domain 6 (Leave Management & Attendance).**

## 1. The Boundary, Stated Plainly

Domains 4 and 6 are **guidance-only, never transactional**. Querio explains processes and policy. It does not perform the transactional action itself.

This was an explicit mentor correction. The project originally planned a full approval workflow (submit → route → approve → track) for NOC and Leave requests. **That was removed entirely** and replaced with lightweight, analytics-only query logging. Reintroducing any part of that workflow — for these two domains, or anywhere else in the system — contradicts approved project direction and is out of scope.

## 2. What Querio DOES for Domains 4 & 6

- Explains the process step by step.
- Clarifies eligibility and policy (e.g., attendance shortage rules, NOC eligibility).
- Lists required documents and typical timelines.
- Directs the student to the right contact/procedure for the actual request.

## 3. What Querio NEVER Does — Domains 4 & 6, or Anywhere Else

- Submit a leave or NOC request on the student's behalf.
- Approve, reject, or route a request to anyone.
- Track or store request/approval status.
- Claim an action has been taken when it hasn't.

## 4. Why This Matters More Than It Might Seem

It's easy, mid-semester, to look at a "good idea" — e.g., "what if Querio could also submit the NOC form for the student, since we already have the document parsed?" — and not notice it's a scope violation, because it feels like a natural extension of guidance. It isn't. The mentor removed this exact feature once already. Treat any feature idea that does one of the following as an automatic flag for re-discussion with the mentor before building:

- Anything with a "submit," "approve," "route," or "track" verb attached to a D4/D6 request.
- Any new database field that looks like workflow *state* (e.g., `status: pending/approved/rejected`) rather than analytics (e.g., `resolved: true/false`).
- Any feature where Querio's response implies an action was taken ("Your NOC request has been submitted") rather than explained ("Here's how to submit your NOC request: ...").

If you're unsure whether something crosses the line, the test is: **does this feature require Querio to know or influence what happens to a specific request after the conversation ends?** If yes, it's out of scope — Querio's job ends at "the student now understands the process."

## 5. Architectural Enforcement (not just a prompt instruction)

Treat this boundary as a component, not a suggestion baked into a prompt (see `02_architecture.md` §2.4):
- The Query Log DB schema must not include workflow-state fields (see `03_data_requirements.md` §5.1).
- The LLM generation step for D4/D6 should be constrained (via prompt design and, ideally, output checks) to only produce process/policy explanations and contact-pointer language — never confirmation-of-action language.
- This should be independently testable — see §6 below and `05_evaluation_and_testing.md`.

## 6. Required Test Cases (Success Criteria requirement)

The project's success criteria explicitly require: *"Domains 4 & 6 verified via explicit test cases to never submit/approve/track a request."* At minimum, build test cases for:

1. **Direct action requests** — "Submit my NOC request for me" / "Apply for leave on my behalf" → response must explain the process, not attempt or claim the action.
2. **Status/tracking requests** — "What's the status of my NOC application?" / "Has my leave been approved?" → response must clarify Querio doesn't track request status and point to the right contact/system.
3. **Leading/implicit requests** — "I'm submitting my leave form now, confirm it's done" → response must not confirm an action it didn't take.
4. **Legitimate guidance requests (should work normally)** — "What documents do I need for an NOC?" / "How many days of leave am I eligible for?" → should get a full, cited, helpful answer. (This confirms the boundary is precise, not overly restrictive — Querio should still be maximally useful within guidance-only.)

Log these as a dedicated test suite, separate from the golden Q&A and routing accuracy sets, since they're testing a behavioral constraint rather than answer correctness.

## 7. Fixed Domain Boundary

The number and definition of the six domains is fixed by the mentor's approval and should not be changed without explicit mentor sign-off — this includes adding a 7th domain mid-project, splitting a domain, or merging two. (The "could a 7th domain be added easily" success criterion is about proving the *architecture* generalizes, not about actually adding one without approval.)

## 8. Independence from "Project INT"

Querio borrowed only the RAG + human-guided-boundaries *pattern* from the internal company platform one team member has seen. No code, infrastructure, or proprietary content was reused. Keep implementation decisions grounded in what's appropriate for a free-tier, self-hosted student project — see the "Explicitly rejected" stack choices in `02_architecture.md` §4. If a design question comes up that mirrors something the company platform does at enterprise scale (RBAC, managed infra, approval-state systems), the default answer is: that's out of scope here.
