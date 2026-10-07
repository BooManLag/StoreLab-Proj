# Operations: how StoreLab actually runs

Philippines (Metro Manila base), B2B. Built from `idea.md`, `offer.md`, `numbers.json` and `pilot-numbers.json`. Amounts are in PHP. Prices were looked up on 2026-10-07 and change, so confirm them before you rely on them.

## 1. The daily and weekly cycle

StoreLab has two jobs running side by side: **pilots** (the 8-Week Store Test) and **Core** (month-to-month stores). 👁 marks a step the customer sees.

**Every day**
1. 06:00 edge boxes in each pilot store upload last night's **anonymised** counts and tracks (no faces or raw video leave the store). An automatic check flags any missing camera.
2. 08:30 review the overnight data-health board. Message the store's IT contact before 10:00 if a camera dropped 👁.
3. 09:00–12:00 analyst time: refresh the store model with yesterday's POS export, re-run open experiments.
4. 13:00–17:00 sales: outreach, camera-readiness checks, kick-off calls 👁.
5. 17:30 log incidents and open questions in the tracker.

**Every week**
- Monday: a one-page progress note per pilot (test vs control so far, data health) 👁.
- Wednesday: one store visit per active pilot (fixture check, camera angles, staff questions) 👁.
- Friday: weekly reorder and kit check (see SOP 5), invoicing, and the three marketing numbers.

**Pilot lifecycle (8 weeks)**
1. Free camera-readiness check: 1 day of footage from 2 stores 👁
2. Contract: KPI, minimum lift, test and control stores set **by the chain** in writing 👁
3. Week 0: install edge boxes, privacy signage, data-processing agreement signed 👁
4. Weeks 1–2: baseline. Weeks 3–8: the change is live in test stores
5. Week 9: peso payback readout 👁. Refund within 14 days if the test stores did not beat the control stores
6. Week 13: the 4-week follow-up reading 👁

## 2. Suppliers

| input | suppliers to contact | public price / how to get it | terms and lead time |
| --- | --- | --- | --- |
| **Gemini model calls** (agent reasoning) | [Google AI / Vertex AI](https://ai.google.dev/pricing) | Gemini 2.5 Flash about USD 0.30 per million input tokens and USD 2.50 per million output tokens; Flash-Lite USD 0.10 / 0.40 ([summary of Google's page](https://www.morphllm.com/gemini-api-pricing), checked 2026-10-07). An experiment run uses tens of thousands of tokens, so this is centavos per run | Pay-as-you-go, monthly billing by card; no minimum |
| **Cloud compute and storage** (simulation, dashboard) | Google Cloud (Cloud Run, Cloud Storage); alternatives AWS, Azure | [Google Cloud pricing calculator](https://cloud.google.com/products/calculator). Apply to [Google for Startups Cloud Program](https://cloud.google.com/startup) for credits | Pay-as-you-go; credits approval takes weeks |
| **Edge box** (runs the camera model inside the store) | NVIDIA Jetson Orin Nano Super kit via local distributors; mini-PCs with a GPU as a fallback | Jetson Orin Nano Super Developer Kit **USD 249** list ([Phoronix](https://www.phoronix.com/news/NVIDIA-Jetson-Orin-Nano-Super)), roughly PHP 14,000–15,000 plus shipping and duties. **Local quote needed** | Stock varies; allow **3–6 weeks** for imports. Order pilot kits right after a contract is signed |
| **Network switch, PoE injectors, cables, UPS** | Local IT suppliers (e.g. stores in Gilmore, Quezon City), online marketplaces | Get 2 quotes | Same week |
| **Privacy signage** (CCTV notice in the store) | Any local print shop | Get quotes; A4 acrylic signs are inexpensive | 2–3 days |
| **Data Privacy Act counsel** | A Philippine law firm with a data-privacy practice | Quote (`numbers.json` estimates PHP 150,000 once plus PHP 20,000/month) | Engagement letter; 2–4 weeks for a DPIA and opinion |
| **Accountant / bookkeeper** | Local CPA firm or freelance bookkeeper | Quote | Monthly retainer |

### ⚠ A cost the CFO numbers are missing: the edge box in Core stores

`numbers.json` assumes **PHP 450 per store-month** for compute. That covers cloud, but **not a box in every Core store**. If each Core store needs its own edge box (about PHP 15,000, written off over 24 months ≈ **PHP 625 per store-month**):

- contribution falls from PHP 2,520 to about **PHP 1,895** per store-month (63%)
- break-even rises from 120 to about **158 paying stores** (300,000 ÷ 1,895)

**Recommendation:** charge a **one-time hardware fee of PHP 15,000 per Core store** (the chain owns the box). Then `numbers.json` stays correct and nothing changes. Pilots keep using **loaned** boxes (already in the PHP 40,000 delivery cost). Decide this before the first Core contract. If you choose to absorb the box instead, add the line to `numbers.json` and re-run `/founder-cfo`. `numbers.json` was **not** changed.

## 3. People

Wage assumptions are the CFO's estimates (`cfo-sources.md`). For reference, the NCR non-farm minimum wage is **PHP 755/day** from 25 July 2026, rising to PHP 780 on 20 January 2027 ([WageIndicator](https://wageindicator.org/ai/work/minimum-wage/countries/philippines/2625-ncr-national-capital-region/)). Technical roles pay well above it. Payroll extras (SSS, PhilHealth, Pag-IBIG, 13th-month pay) are on top: **ask the accountant**.

| role | does | slow first months (0–4 pilots) | at plan (≈150 Core stores) |
| --- | --- | --- | --- |
| Founder A (product/engineering) | Models, edge setup, data health, readouts | Full time, unpaid in year 1 (lean plan) | Full time |
| Founder B (sales/customer) | Outreach, camera checks, kick-offs, store visits | Full time, unpaid in year 1 | Full time |
| Engineer 1 | Pipeline, dashboard, reliability | Full time (the one paid hire in the lean plan) | Full time |
| Engineer 2 | Scale, integrations (POS exports) | — | Full time |
| Sales and customer success | Account management, renewals | Founder B covers it | Full time |
| Field technician | Installs, store visits | Part-time freelancer per install | Part time |

**Weekly rota at the slow start (Mon–Fri, plus on-call)**

| | Mon | Tue | Wed | Thu | Fri | Sat/Sun |
| --- | --- | --- | --- | --- | --- | --- |
| Founder A | data health, readouts | build | store visit | build | kit check | on-call for data alerts (rotating) |
| Founder B | outreach | camera checks | store visit | outreach | invoicing, numbers | — |
| Engineer 1 | build | build | build | build | release + review | on-call (rotating) |

## 4. Routines (one page each)

### SOP 1: Camera-readiness check (free, before signing)
1. Get written permission from the chain to view 1 day of footage from 2 stores.
2. Copy the footage **on-site or by secure transfer**. Never by email or chat.
3. Run the readiness script: resolution, frames per second, angle coverage of aisles and checkout.
4. Score each camera pass / fix / fail. A "fix" says exactly what to change (angle, height, lighting).
5. Delete the footage within 7 days and log the deletion.
6. Send the result email the same week (template in `brand.md`, touchpoint 2).

### SOP 2: Pilot install day
1. Confirm the visit time with the store manager 48 hours ahead.
2. Bring the kit: edge box, power supply, UPS, switch, cables, privacy signs, checklist.
3. Put up privacy notices at every entrance **before** turning anything on.
4. Connect the edge box to the camera network (read-only stream). Never change the chain's NVR settings.
5. Test: counts appear on the dashboard within 30 minutes.
6. Brief staff: what the box does, who to call, "no faces are stored".
7. Photo of the install. Sign-off by the store manager.

### SOP 3: The weekly pilot note and the final readout
1. Pull test vs control on the agreed KPI only.
2. Mark data gaps clearly. Never fill them silently.
3. Weeks 1–8: one page, sent Monday 10:00.
4. Week 9: the peso payback readout. If the test stores did not beat the controls, **start the refund the same day**.

### SOP 4: Handling a complaint
1. Reply within 4 working hours: "We've got it, here is who is on it."
2. Get the facts (store, time, what happened). Check the logs.
3. Fix or explain in plain words within 2 working days.
4. For any privacy complaint, involve the Data Protection Officer at once. A suspected personal-data breach follows the NPC breach rules (notification within 72 hours where required).
5. Log it and review it at the Friday meeting.

### SOP 5: Friday kit check and reorder
1. Count spare edge boxes, power supplies, switches and signs.
2. Keep at least **2 spare kits** at all times. Reorder boxes when spares fall to 2 (allow 3–6 weeks).
3. Check the cloud bill against budget (alert at 80%).
4. Check every edge box's last check-in time. Visit any box silent for over 24 hours.

## 5. Tools (the smallest stack)

| need | tool | published price | why |
| --- | --- | --- | --- |
| Email, docs, calendar | Google Workspace Business Starter | about **PHP 280/user/month** ([Z.com reseller page](https://web.z.com/ph/google-workspace/); check Google's own page) | Same vendor as the cloud; one login |
| Cloud | Google Cloud | pay-as-you-go | Already used by the product |
| Payments (B2B) | Bank transfer and checks with official receipts; online invoicing through the bank | bank fees (~1% in `numbers.json`) | Chains pay by transfer on terms |
| Bookkeeping | A local cloud accounting tool your accountant supports, or the accountant's own system | quote | Must produce BIR-compliant books and receipts |
| Tracker | A shared sheet or the free tier of a task tool | free | Pilots, incidents, open questions |
| CRM | A shared sheet until 30 accounts | free | Only a few hundred named buyers |

## 6. Licences, permits and insurance (checklist)

Rules differ by city and change. Confirm each with the authority or a professional. **Not legal advice.**

- [ ] **Business registration with the SEC** (corporation, or a One Person Corporation) through [eSPARC](https://esparc.sec.gov.ph/). Name reservation PHP 120, then filing fees ([Wise summary](https://wise.com/ph/blog/sec-business-registration)). A sole proprietorship registers with [DTI BNRS](https://bnrs.dti.gov.ph/) instead.
- [ ] **Barangay clearance and Mayor's/business permit** from the city where the office is (each LGU has its own fees and forms).
- [ ] **BIR registration** (Form 1903 for corporations), the **Certificate of Registration (Form 2303)**, books of account and invoices ([BIR](https://www.bir.gov.ph/)). The annual registration fee was removed by the Ease of Paying Taxes Act. Decide **VAT** registration with the accountant (12% if registered).
- [ ] **SSS, PhilHealth and Pag-IBIG** employer registration before the first hire.
- [ ] **Data Privacy Act (RA 10173):**
  - Appoint a **Data Protection Officer**.
  - Check whether StoreLab must **register with the NPC**. Registration is required for organisations that process personal data of 1,000+ people or do high-risk processing; in-store camera analytics may qualify ([NPC registration guide summary](https://www.tripleiconsulting.com/navigating-npc-registration-strategies-for-philippine-business-compliance/)).
  - Follow **[NPC Circular 2024-02 on CCTV systems](https://privacy.gov.ph/wp-content/uploads/2024/08/NPC-Circular-No.-2024-02-CCTV-Systems.pdf)**: notices, purpose limits, retention.
  - In each pilot, the **chain** is usually the personal information controller and StoreLab the **processor**: sign a data-processing agreement every time.
- [ ] **Insurance:** professional indemnity / errors and omissions, cyber liability, and cover for loaned equipment in stores. Get broker quotes.
- [ ] **Import of edge boxes:** check with the supplier or a customs broker whether duties or NTC rules apply.

## 7. Risk register

| # | what goes wrong | likely | how bad | the plan |
| --- | --- | :---: | :---: | --- |
| 1 | **The simulator's prediction is wrong** and pilots claim the refund | medium | high | Stop selling at 3 refunds out of 5 (`offer.md`). Pick the change with the widest safety margin. Re-fit on each pilot's baseline |
| 2 | A **camera feed is too poor** after signing | medium | medium | SOP 1 before every contract; fallback to POS-only KPIs; a bought camera only with the chain's approval |
| 3 | **Privacy complaint or breach** | low | very high | No faces or raw video leave the store; DPO; DPIA; 72-hour breach process; cyber insurance |
| 4 | **Edge boxes out of stock** | medium | medium | Keep 2 spare kits; second supplier; mini-PC fallback |
| 5 | The chain **doesn't move the fixtures** on time | high | medium | Install-day checklist; the date is in the contract; the pilot clock starts when the change is live |
| 6 | **A key person is sick or leaves** (2 founders + 1 engineer) | medium | high | Written SOPs; shared passwords in a password manager; the code in the repo with a README |
| 7 | **Slow sales**: 0 pilots by 31 Dec 2026 | high | high | Weekly numbers (`marketing.md`); go back to `/founder-offer`; supplier co-funding channel |
| 8 | **Late payment** by a chain (60–90-day terms) | high | medium | 50% of the pilot fee up front; keep 6 months of cash |
| 9 | **Cloud bill spikes** | low | low | Budget alerts at 80%; Flash-Lite for routine calls |
| 10 | **Name or trademark dispute** with StoreLab Australia | medium | medium | Rename before selling (`brand.md`); trademark search and filing |

**Open questions for quotes:** local Jetson price and lead time; counsel's fee for the DPIA and opinion; insurance premiums; the LGU business permit fee; whether NPC registration is required.
