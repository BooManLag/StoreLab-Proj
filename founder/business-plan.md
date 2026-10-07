# StoreLab · Business plan

*All amounts are PHP: the tool prints "$". "A day" means a month here (`days_per_month: 1`), and the unit is one paying store for one month.*

**Verdict: Not yet**

- ✓ Each store-month earns $2520.00 before fixed costs (84% contribution).
- ✗ Year 1 operating LOSS: $2,995,200.
- ✗ 2 of 20 simulated buyers buy (10%, the bar is 25%).

| key number | |
| --- | ---: |
| Price | $3000.00 a store-month |
| Profit margin at plan | 17% per store-month |
| Break-even | 120 store-months a day |
| Year 1 operating profit | $-2,995,200 |
| Startup spend | $400,000 |
| Cash needed before it pays for itself | $3,395,200 |
| Startup money earned back | not in year 1 |
| Buyer panel | 2 buy · 18 pass |

## The idea

- What it is: A/B testing for physical retail — software that turns existing store CCTV and POS data into a behavioural "digital twin" of a store, lets an AI agent (Gemini) design store-layout and merchandising experiments for a stated goal, simulates them on synthetic shoppers, and recommends which one is worth a real-store pilot.
- Who it is for: physical retailers who change layouts and displays without knowing what will work. First segment is OPEN — the founder asked the board to recommend one of: mid-size Philippine convenience/mini-mart chains (20–500 stores, existing CCTV), JAPAC supermarket/grocery chains, or mall-based specialty/department retailers.
- What it sells, at what price: a SaaS platform (store analytics + AI experiment design + simulation + pilot planning). Price: NOT DECIDED (open question; per-store subscription and per-pilot fees are both being considered).
- Where and how: software-first and hardware-agnostic (uses cameras the store already has plus POS exports), deployed on Google Cloud (Cloud Run, Gemini on Vertex AI). JAPAC-first: multilingual goals (EN/JA/KO/ID/FIL), anonymous tracking only (no faces, no identity). Delivered as a web app; the output is a pilot plan (test vs control stores, duration, success metric).
- Budget and constraints: currently a hackathon entry (AI Builder Cup by Hack2skill, Retail & Commerce theme), submission due 2026-10-18; working MVP exists on synthetic demo data only — no customers, no real store data yet. Funding budget and team size not stated.

## Summary

**Verdict: Not yet** (computed by `compile.py`). Two checks fail:

- **Year 1 is an operating loss of PHP 2,995,200** (on the full team plan). What changes it: the lean team in `cfo.md` (PHP 1,195,200 loss, break-even 60 stores) and real pilots that start the ramp sooner. Run `/founder-cfo` again once real salaries and quotes are in.
- **Only 2 of 20 simulated buyers buy (10%; the bar is 25%).** The blocker is trust, not price: "no Philippine chain like mine has done this". What changes it: a real pilot result in pesos, which is exactly what the launch test produces. Then `/founder-offer` and `/founder-consumer` again.

**What it is.** StoreLab (working name) lets a Philippine mini-mart chain test a store change (an endcap, a shelf move, a checkout display) on its own camera and POS data, then proves it in 2–3 test stores against matched control stores. It is for operations and merchandising heads at chains of 60–200 stores who already run trials but can't prove what worked.

**The three numbers.** Each paying store-month leaves **PHP 2,520 (84%)** at PHP 3,000. **Break-even is 120 paying stores** (60 on the lean plan). **Year 1: −PHP 2,995,200**, with about **PHP 3.4M** of cash needed before it pays for itself (about PHP 1.6M lean).

**Where the board and the panel agreed:** the pain is real (trials without control stores) and trust is the gap. The 8-Week Store Test with a money-back guarantee moved the panel from 0% to 10%, mostly by removing the price and lock-in objection. **Where they differed:** the board saw a strong wedge in existing cameras plus simulation. The panel distrusted "simulation" and wanted a named peer result.

**Biggest risk:** the simulator's predictions don't hold in real stores, so pilots claim the refund. **Plan:** stop selling after 3 refunds in the first 5 pilots, pick changes with a wide safety margin, and re-fit the model on each pilot's own baseline (`ops.md`). Second risk: the name "StoreLab" is used by an Australian store-simulation company, so rename before selling (`brand.md`).

**What's needed to start:** about PHP 1.6M on the lean plan (PHP 3.4M full team), and the real test in `launch.md`: **3 paid pilots from 60 named buyers by 31 December 2026**. Hold the hires until the pilots are signed.

**This week:** submit the hackathon by **18 October**, then pick the company name from the shortlist and run the trademark search.

*The panel is simulated buyers and every number is a projection from estimates. Real buyers and real quotes confirm them. Not financial, legal or tax advice.*

## What the board said

**Vote: 3 × FUND IF · average score 4.3 / 10** (Offers 4 · Monopoly 4 · Product 5)

### Risks more than one member raised (most dangerous first)

1. **No real-world proof yet (all three).** Today the simulator has only matched synthetic data made by the same model family. Until it ranks a real winner above a real loser, the core promise ("we predicted this would work") does not exist.
2. **The pain, the money and the path to buyers are unknown (Offers, Monopoly).** There is no team size, budget, sales channel or first customer yet. Nobody knows whether mid-size chains feel bad layout guesses as a big pain, or have budget for it.
3. **Too broad, and close to what the incumbent sells (Monopoly, Product).** Most of what StoreLab does (heatmaps, paths, POS correlation, pilot tests) RetailNext already sells. Only "simulate before you move the shelf" is new. RetailNext could add a simulator on top of its own data.
4. **Hand-offs StoreLab does not control (Offers, Product).** Camera quality, POS formats, head-office approval and staff moving fixtures all sit outside the product. How long until a chain sees its first useful result is unknown.

### Conditions (a checklist for the rest of the pack)

- [ ] **One design-partner chain** shares real CCTV and POS data (within ~60 days, per the Monopoly lens).
- [ ] **One real pilot.** Simulate first, then run it with test and control stores, and publish whether the simulator's ranking matched reality, even if it did not. *(All three lenses.)*
- [ ] **Narrow to one hero flow.** One segment, one decision type (endcap and display placement), one goal type (category sales lift under a checkout-queue limit). Other languages, segments and goal types wait.
- [ ] **A guarantee-led first offer.** A fixed-scope, named "first experiment" (readiness check → recommendation → pilot plan → readout), paid per pilot with an outcome or refund guarantee. A per-store subscription only after trust is earned. Price points: `/founder-pricing`, `/founder-cfo`.
- [ ] **An onboarding spec that closes the hand-offs.** Minimum camera and POS requirements, a data-readiness check before any promise is made, and a named owner for every step up to the pilot readout.
- [ ] **Evidence the segment has pain and budget**, plus a written path to the first 10 chains with a cost per customer won (`/founder-consumer`, `/founder-cfo`).
- [ ] **A competitor scan.** Who else sells AI layout simulation to Philippine and JAPAC chains (`/founder-competitors`).

### Recommended first customer (unanimous)

**(a) Mid-size Philippine convenience and mini-mart chains (20–500 stores, existing CCTV).**
- It is one country and a short list of nameable chains: a small market StoreLab could dominate.
- Repeated store formats mean test and control stores come built in, and lessons carry from store to store.
- The MVP is already built on a convenience store, and the segment matches the "use your existing CCTV" promise.
- It avoids the regional incumbent where that incumbent is strongest.

Expand to JAPAC grocery once there is a track record of real rankings. Mall retailers are the hardest of the three: one-off layouts, plus landlords and brands in the loop.

### Where the members disagreed

- **Price model.** The Offers lens wants per-pilot pricing with a guarantee first. The Product lens leaves the choice open but asks which model makes the first pilot easiest to say yes to.
- **What the advantage is.** The Monopoly lens sees the moat in calibration data that builds with every real pilot. The Offers lens sees the near-term advantage in running on existing cameras, with less effort than the incumbent's sensor.

### The strongest version the board can see

StoreLab should not be a retail analytics platform. It should be **a guaranteed "first experiment" service for Philippine convenience chains, delivered by software.** The chain runs one pilot on its existing cameras and pays only if the recommended endcap or display change beats the control stores. Every pilot sharpens the simulator. After 10 or more pilots, the track record ("our simulator picked the winner X times out of Y") becomes the product, and per-store subscriptions follow.

That is narrower than what was pitched: drop the multi-segment, multilingual, every-goal-type scope for now. For the hackathon the current breadth is fine. For the business, it is the main thing to cut.

## The competition

Researched 2026-10-07 from public sources only. Where a page could not be read, it is marked. Full rows are in `competitors.csv`.

### 1. Who is there, from most direct to least

| name | type | what it sells | price for the comparable item | positioning (their words) |
| --- | --- | --- | --- | --- |
| [RetailNext](https://retailnext.net/pricing) | direct | In-store analytics on its own Aurora sensor: traffic, shopper paths, merchandising, pilot-vs-control testing | **Not public.** Per-store monthly quote. A third-party estimate is ~USD 500 per sensor to install plus ~USD 100–250 per sensor per month ([KI-Syndikat](https://www.ki-syndikat.de/tools/retailnext/), "from analyst reports", checked 2026-05-31) | "Discover pricing for retail intelligence that DELIVERS." |
| [InContext Solutions (ShopperMX)](https://www.incontextsolutions.com/shopper-insights/) | direct (simulation) | Online virtual-store simulations with real shoppers, to test shelves, displays and layouts before a rollout. Sold to retailers and CPG brands | Not public | "Now you know." / "Insights predictive of in-store results" |
| [Agrex AI (AIVIS)](https://agrexai.com/retail) | indirect | AI video analytics on existing IP cameras: footfall, dwell, queues, conversion | Not public | "Retail Footfall Analytics: Measure What Drives Revenue" |
| [FootfallCam](https://www.footfallcam.com/Home/WhereToBuy/Philippines) | indirect | People counters, cameras, AI boxes, analytics. Three Philippine resellers (Pasig, Sta Mesa, Makati) | Not public (quote via reseller) | "People Counting System with Support & Services" |
| [V-Count](https://v-count.com/llms-faq.txt) | indirect | 3D people-counting sensors plus the BoostBI analytics package | Priced per sensor; the exact price was not confirmed on the page read | not found |
| [Sensormatic ShopperTrak](https://www.businesswire.com/news/home/20260922180527/en/Sensormatic-Solutions-Predicts-2026s-Busiest-Holiday-Shopping-Days-in-Asia-Pacific) | indirect | Traffic counting and analytics, including Asia Pacific (Johnson Controls) | Not public | not found |
| [VIGI by TP-Link](https://www.vigi.com/ph/blog/2680/cctv-for-retail-stores-in-the-philippines-full-guide/) | indirect | Philippine CCTV with built-in people counting (head-and-shoulder detection, no facial recognition) | Hardware price not read | not found |
| Trial-and-error resets | substitute | Change the floor, wait, compare sales, undo | Labour plus any lost sales | — |
| POS reports plus a store walk | substitute | Category sales from the POS; no path or dwell data | Staff time | — |
| Supplier-funded displays | substitute | Brands propose and often pay for endcaps; the retailer decides placement | Often funded by the supplier (common trade practice; no Philippine source read) | — |

### 2. Price range for the comparable item

**No direct competitor publishes a price**, so there is no honest lowest, median or highest. The only figure found is a third-party estimate for RetailNext: ~USD 100–250 per sensor per month plus ~USD 500 per sensor to install ([source](https://www.ki-syndikat.de/tools/retailnext/)). A store has at least one sensor per entrance, so this is a lower bound per store. `/founder-pricing` should treat it as an anchor to check, not a fact.

### 3. Positioning map (text)

Axes that matter to this buyer: **what the tool tells you** (measure what happened → predict what to change), and **effort to start** (new hardware and installers → existing cameras and data).

```
                     PREDICT what to change
                              |
     InContext ShopperMX      |        (StoreLab aims here)
     (virtual store, online   |        existing cameras + simulation + pilot plan
      shopper panels)         |
                              |
 NEW HARDWARE ----------------+---------------- EXISTING CAMERAS / DATA
                              |
     RetailNext (own sensor;  |        Agrex AI, VIGI people counting
      also runs physical      |        (existing CCTV, counts and heatmaps)
      pilot-vs-control tests) |
     V-Count, FootfallCam,    |
     ShopperTrak (counters)   |
                              |
                     MEASURE what happened
```

RetailNext sits between the two rows: it measures, and it also runs real pilot-vs-control tests. But it asks you to change the real floor first.

### 4. What their customers complain about (thin)

| theme | evidence | status |
| --- | --- | --- |
| Price of hardware plus subscription | A G2 review snippet in search results described RetailNext as very expensive, with "expensive cameras and an expensive software subscription". The page itself returned 403, so the quote is **not verified** ([G2](https://www.g2.com/products/retailnext/reviews)) | **thin**: one review, unverified |
| Lag when switching between many locations | Same G2 snippet, unverified | **thin** |
| Pricing that scales by entrances, even if you use one module | Stated by Spot AI, **a competitor** ([page](https://www.spot.ai/compare/limitations/retailnext-limitations)) | **thin**: competitor's claim |
| No public reviews at all | RetailNext has 0 reviews on [Software Advice](https://www.softwareadvice.com/product/549416-RetailNext/) | — |

Honest result: public complaint data for this B2B category is almost empty. Real objections have to come from conversations with buyers (`/founder-consumer` for simulated ones, then real interviews).

### 5. The gap

- **What exists:** measurement tools (counts, paths, heatmaps), some running on existing CCTV (Agrex, VIGI). **Physical** pilot testing (RetailNext). **Online** virtual-store research with human panels (InContext, which claims a "96%" correlation with in-store results).
- **What nobody in the sources does:** take a store's own camera and POS data, let a manager state a goal and constraints in plain language, design the change, pre-screen it against that store's own behaviour, and hand over a sized test-vs-control pilot plan. All without new hardware, and sold to Philippine convenience chains.
- **Where the gap is weak:** InContext already sells "predict before you change", and it claims high accuracy. Agrex already sells "existing CCTV, under 10 days to go live". So StoreLab's gap is the **combination**, plus the local market, not any single feature. That is real but narrow, and only a real pilot that shows the simulator works will make it believable.
- **Market note:** the two biggest Philippine chains are well above the board's "20–500 stores" segment: 7-Eleven ~4,575 stores ([Philstar, 2026](https://www.philstar.com/business/2026/04/14/2520738/despite-middle-east-crisis-7-eleven-track-5000th-store/amp/)) and Alfamart 2,337 ([Context.ph](https://context.ph/2026/05/14/7-eleven-pushes-toward-5000-store-mark-nationwide/)). The mid-size targets are the chains below them (names seen in search results include Ministop, Uncle John's, Dali, O!Save and Lawson; their store counts were not verified). `/founder-consumer` should model those buyers.

### 6. The threat: who could copy this fastest

1. **RetailNext.** It already has paths, POS correlation, pilot testing and offices in the region. A simulation step on top of its own data is a natural extension.
2. **Agrex AI.** It already runs on existing CCTV. Adding an experiment layer is a shorter step for it than building camera ingestion is for StoreLab.
3. **InContext Solutions.** It already sells prediction before change. Adding store-specific camera data would close the "existing cameras" half of the gap.

StoreLab's defence is speed into one local segment, and building up real pilot results that copycats don't have.

### Added during `/founder-brand` (2026-10-07): a same-name competitor

- **StoreLab™ (Australia, Brookvale NSW)** describes itself as "a global leader in VR simulation, focus group and research", whose software "put[s] powerful shopper marketing ideas into a 'life-like' virtual store, with planogramming, analytics and instant trade presentation" ([search-result listing](https://thedirectory.thevrara.com/organization/4684); the page itself failed its TLS check, so this is from the search summary, **not verified**). It is a **direct competitor using the same name and claiming a trademark (™)**: see `brand.md`.
- A separate **StoreLab** (UK, founded 2020) sells a Shopify mobile-app builder ([Shopify App Store](https://apps.shopify.com/storelab?locale=it), [CB Insights](https://www.cbinsights.com/compare/storelab-vs-tapcart)). It is a different category, but adds to name confusion.

## The buyer panel

**2 buy · 18 pass** (10% buy) out of 20 simulated buyers. Seed 7, so the same cards can be dealt again.

These are simulated buyers, not customers. Use this to find objections and weak spots, then confirm the big ones with real people before you spend.

### By segment

| group | buyers | buy rate |
| --- | ---: | ---: |
| Head of operations or merchandising at a 60-200 store chain | 7 | 14%  (thin) |
| Owner-operator of a 20-60 store regional chain | 8 | 12% |
| Commercial or category director at a 200-500 store chain | 5 | 0%  (thin) |

### By buying behaviour

| group | buyers | buy rate |
| --- | ---: | ---: |
| Data-curious tester | 3 | 67%  (thin) |
| Cost cutter | 4 | 0%  (thin) |
| Needs head-office approval | 2 | 0%  (thin) |
| Burned by a tech vendor | 2 | 0%  (thin) |
| Supplier-led displays | 3 | 0%  (thin) |
| Follows the market leader | 2 | 0%  (thin) |
| Gut-feel merchandiser | 4 | 0%  (thin) |

### By income

| group | buyers | buy rate |
| --- | ---: | ---: |
| $54,000 and up | 7 | 14%  (thin) |
| $38,000 to $54,000 | 8 | 12% |
| under $38,000 | 5 | 0%  (thin) |

### Why they pass

| reason | buyers | in their words |
| --- | ---: | --- |
| trust | 15 | "The money-back guarantee is good, but I can't take a new company with no results to my board and ask them to let outsiders plug into our CCTV and POS. If it goes wrong I am the one who recommended it, so this month I would watch, not sign." (P002) · "I already paid once for a system nobody touched after three months, and you're a new company with no results from a single chain yet. I'm not putting my name on a PHP 75,000 request to the owner for a company that has never done this before, refund or no refund." (P003) |
| price | 2 | "The 75,000 test is refundable so that part doesn't scare me, but the test only matters if I roll it out, and 3,000 a store every month across a 300-store chain is close to 11 million pesos a year. With no customer results yet I can't put that in front of finance against what one more merchandiser costs me." (P001) · "The 75,000 pilot with a refund is almost safe, but the pilot is just the door. At PHP 3,000 a store a month across 120 stores that is 360,000 a month, more than 4 million a year, and I can hire a lot of merchandisers for that. A new company with no results cannot show me that payback today." (P009) |
| need | 1 | "Most of our displays are proposed and paid for by the brands, so I mostly just approve placement and fix things myself on weekend store visits. Paying 75,000 to test changes I don't really control is hard to justify, and a new company with no results makes it harder." (P014) |

### Why they buy

| reason | buyers | in their words |
| --- | ---: | --- |
| need | 2 | "I already run small store trials off my Monday POS reports, but I never have proper control stores, so the evidence is always soft. If the result is measured on real test stores against matched controls and I get the fee back when it doesn't win, PHP 75,000 is a risk I can take, as long as the free camera check comes first." (P010) · "I already run small store trials off POS reports and can never prove what caused the lift, so a matched-control test with a full refund if it fails is worth PHP 75,000 to me. That is small enough that I can sign it off without a long fight with the owner." (P018) |

### What would flip a no

- A per-store fee that only kicks in on stores where the change is rolled out, or pricing tied to the extra margin the test proves, so payback within the year is guaranteed on paper.
- One named chain of our size that ran the test and will take my call, plus a contract that makes clear our data stays ours and gets deleted if we stop.
- Speaking to another Philippine chain that ran the test and kept paying afterwards, and having our own lawyer sign off on the privacy opinion before any data leaves our CCTV.
- A result from another Philippine chain I can call, or a pitch that makes the test pay for itself through suppliers, for example proof that endcap slot pricing lets me charge brands more for placement.
- A named chain like mine that ran the test and got a real peso result, and that I can call myself.
- One real result from another Philippine chain my size, showing the peso gain against the monthly fee, plus pricing for continuing that's capped or only charged on the stores that actually gain.
- Seeing a bigger chain like 7-Eleven or Alfamart, or a chain I know, use it and get a real peso result I can show my boss.
- My own lawyer signing off on the privacy setup, plus talking to one of the other first-round chains after their 8 weeks to see if the result was real.
- A guarantee tied to a minimum peso lift that covers the rollout fee, or a rollout priced only on the stores where the change actually ran, plus one named chain that already got a result.
- Seeing real peso results from another Philippine chain like ours, ideally one I know or can call, so I'm not the first to try it.
- Seeing one real chain like mine that ran it, with their result in pesos and confirmation their DPO and the NPC side were clean, ideally with a supplier co-paying the test.
- A real result from one other Philippine chain, in pesos with a payback period, plus a written cap or tiered price for rolling out past the test stores.

Buyers say they would buy **1.0 times** in the first month on average.

20 buyers gave all four price answers. Run founder-pricing's van_westendorp.py on the answers folder.

## Pricing

All amounts are in Philippine pesos (PHP). The pricing-curve and CFO tools print "$", but every figure is PHP. The unit is one **store-month** (one store on StoreLab for one month).

### 1. The price: PHP 3,000 per store per month, month-to-month after a pilot

- **Where it sits in the buyers' range.** The 20-buyer panel's acceptable range is PHP 1,502–5,990 per store per month (`pricing-curve.md`). PHP 3,000 is at the indifference point (IPP PHP 3,008), where as many buyers call it a bargain as call it expensive. The tested PHP 8,000 is **above** the range: every buyer passed, and 15 of 20 put "too expensive" at PHP 8,000 or below.
- **Against competitors.** Nobody publishes a price (`competitors.md`). The only anchor is a third-party estimate for RetailNext of about USD 100–250 per sensor per month plus about USD 500 to install. At roughly PHP 58 to the dollar (an estimate, not a quoted rate), that is about PHP 5,800–14,500 per sensor per month. PHP 3,000 per store with no new hardware is clearly cheaper, so do not compete on price below this.
- **Margin (from the CFO tool, `numbers.json`, cost estimates).** At PHP 3,000 each store-month leaves **PHP 2,520 (84%)** after its own costs. **Break-even is 120 paying stores.** At the plan of 150 stores the profit margin is **17%**.
  - At PHP 1,500 the contribution is PHP 1,020 and break-even needs **295 stores**: too low.
  - At PHP 4,500 break-even falls to **75 stores**, but that price is near the top of the buyers' range.
  - At every price, year 1 loses money, because the ramp is slow (the CFO step covers this).

### 2. The ladder

| rung | what you get | price | why step up |
| --- | --- | --- | --- |
| **First Experiment** (pilot) | 2–3 test stores against matched control stores, about 8 weeks: camera-readiness check, goal → recommended change → simulation → pilot plan → results readout | one fixed fee (amount and guarantee set in `/founder-offer`; target range PHP 50,000–90,000) | The way in. It answers the panel's number-one request: "a short pilot, no 12-month lock-in, results checked against control stores". |
| **Core** | Unlimited goals and simulations for the stores on the plan, monthly pilot plans, basic support | **PHP 3,000 / store / month**, month-to-month, minimum 10 stores | You keep testing after the first win. Monthly billing removes the lock-in objection. |
| **Chain** | Core plus quarterly reset planning across the chain, a named analyst, priority support, and a Data Privacy Act documentation pack kept up to date | **PHP 4,500 / store / month**, 12-month term | For chains running several changes each quarter. The annual term is only offered after Core has shown results. |

### 3. The opening offer (launch, with an end date)

**Design-partner programme: the first 5 chains** (a real limit: one team can run about five pilots at once). The First Experiment fee is credited in full against the first 6 months of Core if the chain continues. The offer ends when 5 chains sign or on **31 March 2027**, whichever comes first. It is not a discount on the list price, so buyers aren't trained to wait for one.

### 4. What to test with real buyers

Test two prices inside the range: **PHP 2,500 and PHP 3,500 per store per month** (the First Experiment fee stays the same).

- **How:** in the first 10–15 sales conversations, alternate which price appears on the one-page proposal. Record which chains ask for a contract and which stall on price.
- **Also run:** a landing page with a "Book a First Experiment" form, showing one of the two prices to each half of visitors.
- **Decision rule:** pick PHP 3,500 unless it closes at least 30% fewer pilots-to-contract than PHP 2,500.

### 5. The panel's price objections, word for word (for marketing to answer)

1. "Even at the 10-store minimum that's PHP 80,000 a month, almost a million a year, locked in for 12 months with a company that has zero results to show me." (P001)
2. "Ten stores minimum at 8,000 each is 80,000 pesos a month, almost a million a year locked in, and that buys several more staff for my stores. A new company with no results can't show me how I get that back within the year." (P006)
3. "Ten stores minimum at PHP 8,000 each is PHP 80,000 a month, almost a million pesos locked in for a year, right after a slow quarter when I'm being told to cut." (P005)

Simulated price answers pick what to test. They are not proof. Real proposals decide the price.

## The offer

Built with the Offers lens (`founder-board/lenses.md`, a summary of a published framework, not anyone's words). Amounts are in PHP. Costs are estimates from `numbers.json` and `pilot-numbers.json`.

### 1. The problem list, in the buyer's words (from the panel and the competitor research)

Before buying
1. "A company with zero results to show me." (14 of 20 passed on trust)
2. "Almost a million pesos locked in for 12 months."
3. "That money hires several more store staff."
4. "A simulation is only as good as its track record."
5. "Our CCTV is old and low resolution. Will it even work?"
6. "Is filming customers for analytics allowed under the Data Privacy Act?"
7. "I'd be the one who recommended it to the board if it fails."
8. "Suppliers already propose and pay for our displays."
9. "7-Eleven and Alfamart don't use it."
10. "No payback figure in pesos."

During
11. "My one IT person already runs the CCTV and the POS."
12. "Who moves the fixtures, and when?"
13. "How long until I see anything?"
14. "I don't know which stores to compare against."

After
15. "What if the lift disappears after the novelty?"
16. "What if the prediction is wrong? I've paid anyway."
17. "Can I stop if it doesn't work?"
18. "How do I show my board or the owner the result?"

### 2. Solutions, scored (value to buyer 1–5 / cost to deliver 1–5)

| problem(s) | solution | value | cost | keep? |
| --- | --- | :---: | :---: | :---: |
| 1, 4, 16 | **Money-back guarantee** if the test stores don't beat the control stores on the agreed KPI | 5 | 3 | ✔ |
| 2, 3, 17 | **No lock-in.** One fixed fee for 8 weeks, then month-to-month Core at PHP 3,000/store | 5 | 1 | ✔ |
| 5 | **Camera-readiness check before signing**: we look at 1 day of footage from 2 stores for free | 4 | 1 | ✔ |
| 6 | **Data Privacy Act pack**: DPIA template, privacy-notice signage, written counsel opinion (shared across clients) | 5 | 2 | ✔ |
| 11 | **Zero IT effort**: StoreLab connects the CCTV and POS export; an edge box is loaned for the pilot | 4 | 2 | ✔ |
| 14 | Matched control stores picked by StoreLab (already built into the pilot plan) | 4 | 1 | ✔ |
| 10, 18 | **Peso payback readout**: test vs control in pesos, one page, ready for the board | 5 | 1 | ✔ |
| 8 | **Endcap value report**: which endcap slots earn most per shopper passing, to price supplier-funded displays | 4 | 1 | ✔ |
| 12 | A fixture-move checklist plus one on-site visit on installation day | 3 | 2 | ✔ |
| 15 | A 4-week follow-up reading after the pilot ends | 3 | 1 | ✔ |
| 9 | Pretending big chains use it | — | — | ✘ never: no fake social proof |
| 7 | Free unlimited consulting | 3 | 5 | ✘ too costly |

### 3. The stack

**Name: the 8-Week Store Test.** It names the result and the time, not the company.

- **Core:** *"Find out in 8 weeks whether a store change sells more, before you roll it out to the chain."* You give StoreLab one goal. It recommends the change, simulates it on your store's data, and runs it in 2–3 test stores against matched control stores. You get the real result in pesos.
- **Bonus 1: Camera-readiness check, free, before you sign** (kills "our CCTV is old").
- **Bonus 2: Data Privacy Act pack** (kills "is this allowed?").
- **Bonus 3: Endcap value report**, which you can use to price the endcaps your suppliers pay for (turns "suppliers decide" into extra supplier income).
- **Guarantee:** if the test stores don't beat the control stores on the agreed KPI, the full PHP 75,000 fee is refunded.
- **Price:** **PHP 75,000** for the 8-Week Store Test. If you continue, the full fee is credited against your first 6 months of Core (PHP 3,000/store/month, month-to-month).
- **Real scarcity:** **5 design-partner slots**, because one team can run about five pilots at once. Offer ends 31 March 2027.

#### What the guarantee costs (CFO tool, `pilot-numbers.json`)

| claim rate | contribution per pilot |
| --- | --- |
| 30% (planning estimate) | **PHP 11,750** (16%) |
| 50% | **−PHP 3,250** (−4%) |

The guarantee is affordable while fewer than about **46%** of pilots claim the refund (PHP 34,250 margin before refunds ÷ PHP 75,000). The first pilot is a door-opener, not a profit centre. The money is in Core: 10 stores × PHP 2,520 contribution × 12 months ≈ PHP 302,400 a year per chain (`numbers.json`). If more than 2 of the first 5 pilots claim the refund, stop and fix the simulator before selling more.

### 4. Value equation, before (v1 pitch) → after (8-Week Store Test), 1–10

| element | before | after | what moved it |
| --- | :---: | :---: | --- |
| Dream outcome | 6 | 7 | Peso payback readout and endcap income |
| Perceived likelihood | 2 | 6 | Guarantee, readiness check, test against real control stores |
| Time to result | 3 | 7 | "8 weeks", instead of an open-ended 12-month contract |
| Effort and sacrifice | 3 | 7 | No lock-in, zero IT effort, Data Privacy Act pack, StoreLab picks the controls |

### 5. Re-test on the same 20 buyers (seed 7, `--quick`)

| | v1 (PHP 8,000/store/month, 12-month lock-in) | v2 (8-Week Store Test) |
| --- | --- | --- |
| Buy | **0 / 20 (0%)** | **2 / 20 (10%)** |
| Pass for **trust** | 14 | 15 |
| Pass for **price** | 4 | 2 |
| Pass for **need** | 2 | 1 |

**What dropped:** the price and lock-in objection ("almost a million pesos locked in"). Most buyers now call the PHP 75,000 fee "small" or "almost safe".

**What did not move:** trust. The new top objection is *"no other Philippine chain has done this"*. 11 of 20 named "a chain like mine with a result in pesos that I can call" as what would flip them.

**New objections the offer created (fix these next):**
1. **"Who decides what 'beat the control stores' means?"** (P006, P009, P010, P015, P017, P018). Fix: write the KPI, the minimum lift and the control stores into the contract **before** the test starts, chosen by the chain.
2. **Roll-out cost across a big chain** ("PHP 3,000 × 300 stores ≈ PHP 11M a year", P001, P009, P013). Fix: charge Core only on stores where a tested change is live, with volume tiers. `/founder-pricing` should model this.
3. **Data and privacy liability stays with the chain** (P008, P012, P020). Fix: data-processing agreement with deletion on exit, and the chain's own counsel reviews it.
4. **Supplier co-funding** (P012, P014, P019): let a brand pay for the test of its own endcap.

The two buyers who said yes (P010, P018) were data-curious operations heads who already run small trials. They are the first audience. Both said yes only if the free camera check passes and the chain sets the KPI.

*The buyer profiles kept the v1 doubt "PHP 8,000 a store adds up"; one buyer flagged the mismatch. Both runs used the same buyers, so the comparison holds. The buy rate is from simulated buyers and is an upper bound.*

---

*Rules followed: every promise is deliverable by the current product. No fake social proof or countdowns. Guarantee terms should follow Philippine consumer and trade rules (B2B contract). Not legal advice.*

## The numbers

*All amounts are PHP. The tool prints "$" and "a day"; here one "day" is one month (`days_per_month: 1`), and the unit is one paying store for one month. Every cost is an **estimate** (`cfo-sources.md`). Replace them with your real salaries and quotes.*

- **The margin:** each store-month earns **PHP 2,520 of contribution (84%)** at PHP 3,000. At the plan of 150 paying stores, the profit margin is **17%**.
- **Break-even: 120 paying stores.** That is about 8–12 mid-size chains putting 10–15 stores each on Core.
- **Year 1 (conservative ramp: 0 paying stores until month 5, 60 by month 12):** operating loss **PHP 2,995,200** on PHP 720,000 of revenue. **Cash needed before it pays for itself: about PHP 3.4M.** The startup spend is not earned back in year 1. Pilot fees (PHP 75,000 each, about PHP 11,750 contribution at a 30% refund rate, `offer.md`) are extra and not in these figures.
- **The line to watch: fixed costs (the team), not price.** The what-ifs:

| change | break-even | year-1 loss | cash needed |
| --- | --- | --- | --- |
| Plan as written | 120 stores | 2,995,200 | 3,395,200 |
| Price PHP 4,500 instead of 3,000 | 75 stores | 2,635,200 | 3,035,200 |
| Twice as many paying stores each month | 120 stores | 2,390,400 | 2,792,800 |
| **Lean team:** 1 paid engineer, founders unpaid in year 1, no separate sales hire | **60 stores** | **1,195,200** | **1,596,400** |

**Three ways to improve the margin**, each measured by the tool:

1. **Run lean in year 1.** Cutting PHP 150,000 a month of payroll halves break-even, from 120 to 60 stores, and saves about PHP 1.8M of cash.
2. **Win Chain-tier customers.** At PHP 4,500 per store, break-even drops from 120 to 75 stores and the year-1 loss shrinks by PHP 360,000.
3. **Shorten the ramp.** Doubling paying stores each month saves about PHP 600,000 in year 1. Volume alone does not fix year 1; the team cost does.

**The board's money conditions** (`board.md`): "evidence the segment has pain and budget" and "a path to 10 chains with a cost per customer" are **not met yet**. The panel buy rate (10% at best, simulated) is not evidence. Real pilots are. The guarantee is affordable while fewer than about 46% of pilots claim it.

*Revenue is before 12% VAT if registered. Not financial, tax or legal advice: an accountant should check the structure, payroll costs (SSS, PhilHealth, Pag-IBIG) and tax before money moves.*

---

## Unit economics: StoreLab (per-store SaaS for Philippine convenience chains; all amounts in PHP; ESTIMATES, see cfo-sources.md)

Every number below comes from the input file. Nothing is looked up or guessed.

### One store-month

| line | per store-month |
| --- | ---: |
| Price | $3,000.00 |
| Cloud compute, video processing, storage, Gemini calls (estimate) | -$450.00 |
| Payment / bank fees ~1% (estimate) | -$30.00 |
| **Contribution** (what each store-month leaves to pay the fixed costs) | **$2,520.00** (84%) |

### The margin that matters

Fixed costs: $300,000 a month (2 engineers (estimate PHP 90k each) $180,000, 1 sales & customer success (estimate) $60,000, Base cloud, tools, software (estimate) $25,000, Legal / data-privacy retainer (estimate) $20,000, Coworking desk (estimate) $15,000).

- **Break-even: 120 store-months a day.** Below that you lose money every month.
- **Profit margin at your plan** (150 a day): **17%** of every sale, after every cost.

### Year 1, month by month

| month | store-months a day | revenue | profit | cumulative (after $400,000 startup) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | $0 | -$300,000 | -$700,000 |
| 2 | 0 | $0 | -$300,000 | -$1,000,000 |
| 3 | 0 | $0 | -$300,000 | -$1,300,000 |
| 4 | 0 | $0 | -$300,000 | -$1,600,000 |
| 5 | 10 | $30,000 | -$274,800 | -$1,874,800 |
| 6 | 10 | $30,000 | -$274,800 | -$2,149,600 |
| 7 | 20 | $60,000 | -$249,600 | -$2,399,200 |
| 8 | 20 | $60,000 | -$249,600 | -$2,648,800 |
| 9 | 30 | $90,000 | -$224,400 | -$2,873,200 |
| 10 | 40 | $120,000 | -$199,200 | -$3,072,400 |
| 11 | 50 | $150,000 | -$174,000 | -$3,246,400 |
| 12 | 60 | $180,000 | -$148,800 | -$3,395,200 |

- **Year 1 operating profit: -$2,995,200** on $720,000 of revenue.
- After the $400,000 startup spend: -$3,395,200.
- Startup money earned back: not within year 1.
- Cash you need before it pays for itself: **$3,395,200**.

### What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | 17% | 120 | -$2,995,200 |
| Price -10% | 8% | 136 | -$3,067,200 |
| Volume -20% | 1% | 120 | -$3,116,160 |
| Unit costs +15% | 15% | 123 | -$3,012,480 |

### Red flags

- Year 1 loses money on operations (-$2,995,200).
- The startup spend is not earned back within year 1.

## Marketing

Built from `panel/results.md` (v2, 10% simulated buy rate), `panel-v1/results.md` (0%), `competitors.md`, `offer.md` and `pricing.md`. Amounts are in PHP.

### 1. Positioning

**First audience (from the panel):** the two buyers who said yes were **data-curious heads of operations or merchandising at 60–200-store chains** who already run small store trials but can't prove what caused a lift. Owner-operators who go by gut feel, and "follow the leader" buyers, all passed. Do not lead with them.

Three versions:

1. **(Recommended)** *For operations heads at Philippine mini-mart chains who already test store changes but can't prove what worked, the 8-Week Store Test is the store-experiment service that proves a change against matched control stores, using the cameras you already have, with your money back if it doesn't win. Unlike people counters and heatmaps that only show what happened, it tells you what to change and proves it.*
   - **Panel evidence:** P010 and P018 bought because "my trials never had proper control stores". The guarantee cut the price objection from 4 buyers to 2.
2. *For chains whose endcaps are paid for by suppliers, StoreLab shows which display slots are worth the most, so you can price them.* Speaks to the "suppliers decide our displays" objection (P012, P014, P019). Keep it as a secondary message: it answers "need" but not "trust".
3. *Simulate before you move a shelf.* The product's own idea, but the panel distrusted "simulation" (14 of 20 passed on trust in v1). Use it in the demo, not in the headline.

**Do not sound like:** RetailNext ("retail intelligence that DELIVERS") or people-counter vendors. Never say "AI predicts your sales". Say "we test it in your stores, and you only pay if it wins".

### 2. Channels (B2B: only a few hundred buyers, reached one at a time)

| channel | why it fits | rough cost | how you know it worked |
| --- | --- | --- | --- |
| **Founder-led direct outreach** (LinkedIn plus warm intros to operations and merchandising heads) | The first audience is a few hundred named people. The panel wanted "someone I can call" | time only; LinkedIn premium about PHP 2,000–3,000/month (check current price) | 30 messages/week → ≥ 5 calls/week |
| **Retail associations and events in the Philippines** (for example the Philippine Retailers Association and its events; confirm membership terms and dates on their own sites) | Where chain operators gather, and it creates "I saw other chains there" | membership and booth: get quotes (not looked up) | ≥ 10 qualified conversations per event |
| **Supplier co-funding** (FMCG brands' trade-marketing teams) | Answers "suppliers decide displays" and "who pays": a brand co-funds the test of its own endcap | time; discounts are possible | ≥ 1 brand co-funding a pilot |
| *Not doing:* paid social and TikTok, broad search ads | Consumer channels; the buyer is a handful of executives | — | — |

### 3. The 30-day campaign (launch day **Monday 16 November 2026**, after the hackathon on 18 Oct)

| date | channel | what goes out |
| --- | --- | --- |
| Mon 2 Nov (L-14) | LinkedIn (founder) | Post: "Your store trials need control stores. Here's why" (education, no pitch) |
| Tue 3 Nov | Direct | Build a list of 60 named operations and merchandising heads at mid-size chains |
| Wed 4 Nov | Direct | Ask 10 warm contacts for intros |
| Thu 5 Nov | LinkedIn | Short demo video: before/after store simulation (hook 3) |
| Fri 6 Nov | Website | Landing page live: the offer, the guarantee, "Book a free camera check" |
| Mon 9 Nov (L-7) | Direct | First 20 personal messages (hook 1) |
| Tue 10 Nov | LinkedIn | Post: Data Privacy Act explainer for CCTV analytics (hook 6) |
| Wed 11 Nov | Supplier outreach | Email 5 FMCG trade-marketing leads about co-funded endcap tests (hook 8) |
| Thu 12 Nov | Direct | 20 more messages |
| Fri 13 Nov | LinkedIn | "How we pick control stores" (hook 5) |
| **Mon 16 Nov (launch)** | All | Announce the 8-Week Store Test: 5 design-partner slots, ends 31 Mar 2027 (hook 2) |
| Tue 17–Fri 20 Nov | Direct | Follow-ups; book free camera checks |
| Mon 23 Nov (L+7) | LinkedIn | Behind the scenes: running a camera-readiness check (anonymised) |
| Wed 25 Nov | Event / association | Attend or exhibit at a retail event, if one falls in this window (check calendars) |
| Fri 27 Nov | LinkedIn | "What a peso-payback readout looks like": a sample one-pager with synthetic data, clearly labelled |
| Mon 30 Nov – Wed 2 Dec (L+14–16) | Direct | Second round of outreach to everyone who opened but didn't reply; first pilot kick-off, if signed |

On days with nothing new: post a screen from the product, a tip on store testing, or a privacy-by-design detail. Never a fake result.

### 4. Ten hooks, each answering a panel objection

1. "Your last store trial: did it have control stores?" (`no proof` · ad headline)
2. "Pay only if the test stores beat the control stores." (`trust` · LinkedIn and landing headline)
3. "Same shoppers, two layouts. Watch who changes route." (3-second video opener)
4. "No 12-month contract. 8 weeks, then decide." (`lock-in`)
5. "You pick the KPI and the control stores, in writing, before we start." (new v2 objection: "who decides 'beat'?")
6. "No faces. No names. A Data Privacy Act pack your own lawyer can review." (`privacy`)
7. "Works on the cameras you already have. We check them free before you sign." (`old CCTV`)
8. "Your suppliers pay for endcaps. Know which slots are worth the most." (`suppliers decide`)
9. "Results in pesos, on one page your owner will read." (`payback`)
10. "Five chains this round, because we run every test ourselves." (real scarcity)

### 5. Budget and numbers

- **Budget for the first 30 days: about PHP 60,000.** Landing page PHP 15,000. LinkedIn premium PHP 3,000. Demo video PHP 12,000. One event or association fee PHP 30,000 (placeholder until quoted).
- **The most to spend winning one chain.** One chain on Core at 10 stores leaves 10 × PHP 2,520 × 12 = **PHP 302,400 of contribution in year 1** (`cfo.md`), plus about PHP 11,750 from the pilot (`offer.md`). Spending no more than one-third of that gives a ceiling of **about PHP 100,000 per chain won**, including founder time.
- **Three numbers to watch every week:**
  - **Calls booked per week.** Change the message or list if fewer than 3 for two weeks.
  - **Camera checks done.** Fewer than 2 a month means the offer isn't believed.
  - **Pilots signed.** If 0 by L+45 (31 Dec), go back to `/founder-offer`.

*No fake reviews, follower counts or "as seen on". Panel quotes are research, never ad copy. Disclose any paid partnership. Not legal advice.*

## Brand

### 0. The finding that changes everything: "StoreLab" is taken in your category

- **StoreLab™ (Australia)** sells VR store simulation, planogramming and shopper research: the same category, with a claimed trademark (`competitors.md`, unverified listing).
- **StoreLab (UK)** sells a Shopify app builder.
- Domains: `storelab.ai`, `storelab.app` and `getstorelab.com` already have DNS records (registered). `storelab.com` and `storelab.ph` showed no name-server record on 2026-10-07. That does **not** prove they are free.

**Recommendation:** keep "StoreLab" as the **hackathon project name** (it's already submitted and in the repo). Pick a different **company/product name** before selling to chains or filing anything. Confusion with an existing simulation vendor that claims a trademark is a legal and sales risk.

### 1. Ten candidates

| name | style | what it says | out loud / on a sign | risk |
| --- | --- | --- | --- | --- |
| **Tindalab** | local + descriptive | *tinda* (to sell, as in "tindahan") + lab | "TIN-da-lab": easy in Filipino and English | Means little outside the Philippines; fine for a PH-first business |
| **Pasilyo** | local, evocative | Filipino for corridor/aisle | Warm, memorable | `.com` registered; `.ph` showed no DNS record. Unclear to non-Filipinos |
| **ProvenAisle** | descriptive | the promise: changes proven in the aisle | Clear in English | A little long; "proven" is a claim, so it must be earned |
| **Endcap** | descriptive | the thing it tests most | Short, but generic | Hard to trademark; generic retail term |
| **Testfloor** | descriptive | test on the floor | Clear | `floortest.com` taken; a generic phrase |
| **Kontrol** | evocative | control stores | Punchy | Many existing "Kontrol" brands |
| **Pilotwise** | descriptive | smart pilots | Clear | Generic "-wise" suffix; check marks |
| **Abante** | local, evocative | Filipino "go forward" | Strong locally | Common word; existing businesses likely |
| **Gondola** | evocative | the shelf unit | Fun | Gondola brands exist |
| **SariLab** | local | *sari-sari* store + lab | Very local | Points at small sari-sari stores, not chains (wrong audience) |

**Shortlist: Tindalab, ProvenAisle, Pasilyo.**

### 2. Checks to finish yourself (public searches only; nothing is registered until you register it)

- **Trademark.** Search the [IPOPHL trademark database](https://www.ipophil.gov.ph/) (Philippines), the [WIPO Global Brand Database](https://branddb.wipo.int/) and, if you expand, the USPTO and EUIPO. Classes: **9** (software), **42** (SaaS and analytics platform), **35** (market research and business analytics). A trademark lawyer confirms clearance. Not legal advice.
- **Domains** (DNS name-server check on 2026-10-07; confirm at a registrar):

| domain | result |
| --- | --- |
| tindalab.com | no record found |
| tindalab.ph | no record found |
| provenaisle.com | no record found |
| pasilyo.ph | no record found |
| pasilyo.com | **registered** |

- **Handles:** check Instagram, TikTok, X, YouTube and LinkedIn by hand for each name.
- **Confusion:** none of the shortlist is close to a competitor in `competitors.md`. "Store**Lab**" and "Tinda**lab**" share "lab", so check that the Australian StoreLab's mark doesn't cover "-lab" variants in your classes.

### 3. Voice and promise

- **Promise:** *"We prove it in your stores, and you only pay if it wins."*
- **Tagline options:**
  1. "Test it before you roll it out."
  2. "Proof, aisle by aisle."
  3. "Don't rebuild the store to find out." (from the original spec)
- **Voice:**

| adjective | do | don't |
| --- | --- | --- |
| **Plain** | Short sentences, pesos, store words (endcap, aisle, queue) | "AI-powered digital twin synergy" |
| **Honest** | Say what's simulated, what's guaranteed, what isn't known yet | "Guaranteed sales lift" |
| **Practical** | Lead with the next step ("Book a free camera check") | Vision statements first |

- **Before/after, a line from `pitch.md`:**
  - **Before:** "StoreLab recommends the change, simulates it on your own store's CCTV and POS data, then runs it in 2–3 test stores against matched control stores."
  - **After:** "Tell us what you want to sell more of. We pick the change, try it in 2–3 of your stores, compare them with stores we didn't touch, and show you the difference in pesos."

### 4. The look (a brief; it reuses the app's palette for consistency)

| colour | hex | job | contrast check (text on it) |
| --- | --- | --- | --- |
| Ink | `#0B0B0B` | Headlines, primary buttons | White on ink: about 19.6:1 (passes AA/AAA) |
| Insight blue | `#2A78D6` | Links, insight highlights, the "target" aisle | White on blue: about 4.6:1 (passes AA for normal text) |
| Proof green | `#006300` | "Recommended", "Launch pilot", wins | White on green: about 7.6:1 (passes AA/AAA) |

Paper `#F6F5F1` is the background. Amber `#FAB219` is for risk and red `#D03B3B` for constraint breaches; both always come with an icon and a label, never colour alone.

- **Type:** **Inter** for text and **Space Grotesk** for display. Both are free under the SIL Open Font License from [Google Fonts](https://fonts.google.com/).
- **Logo brief:**
  - A simple mark of two aisles: one plain, one with a small check or tick.
  - It must read at a **32 px app icon**, on a **receipt-width one-pager**, and on a **trade-show banner**.
  - Avoid magnifying glasses, brains and circuit lines (generic "AI" clichés).
  - Image-tool concepts would be marked as concepts, not a finished logo.
- **The first five touchpoints:**
  1. **Homepage:** the promise, "Book a free camera check", and the before/after shopper animation.
  2. **Camera-check email:** what was checked, pass/fail per camera, the next step.
  3. **Pilot kick-off one-pager:** the KPI, test stores, control stores and refund rule, signed by both sides.
  4. **First LinkedIn post:** hook 1 from `marketing.md`.
  5. **Reply to the first complaint:** same-day, plain, the facts and the next step, never defensive.

*Never copy a competitor's name, logo, colours or tagline. Only use fonts and images you have the right to. Not legal advice.*

## Operations

Philippines (Metro Manila base), B2B. Built from `idea.md`, `offer.md`, `numbers.json` and `pilot-numbers.json`. Amounts are in PHP. Prices were looked up on 2026-10-07 and change, so confirm them before you rely on them.

### 1. The daily and weekly cycle

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

### 2. Suppliers

| input | suppliers to contact | public price / how to get it | terms and lead time |
| --- | --- | --- | --- |
| **Gemini model calls** (agent reasoning) | [Google AI / Vertex AI](https://ai.google.dev/pricing) | Gemini 2.5 Flash about USD 0.30 per million input tokens and USD 2.50 per million output tokens; Flash-Lite USD 0.10 / 0.40 ([summary of Google's page](https://www.morphllm.com/gemini-api-pricing), checked 2026-10-07). An experiment run uses tens of thousands of tokens, so this is centavos per run | Pay-as-you-go, monthly billing by card; no minimum |
| **Cloud compute and storage** (simulation, dashboard) | Google Cloud (Cloud Run, Cloud Storage); alternatives AWS, Azure | [Google Cloud pricing calculator](https://cloud.google.com/products/calculator). Apply to [Google for Startups Cloud Program](https://cloud.google.com/startup) for credits | Pay-as-you-go; credits approval takes weeks |
| **Edge box** (runs the camera model inside the store) | NVIDIA Jetson Orin Nano Super kit via local distributors; mini-PCs with a GPU as a fallback | Jetson Orin Nano Super Developer Kit **USD 249** list ([Phoronix](https://www.phoronix.com/news/NVIDIA-Jetson-Orin-Nano-Super)), roughly PHP 14,000–15,000 plus shipping and duties. **Local quote needed** | Stock varies; allow **3–6 weeks** for imports. Order pilot kits right after a contract is signed |
| **Network switch, PoE injectors, cables, UPS** | Local IT suppliers (e.g. stores in Gilmore, Quezon City), online marketplaces | Get 2 quotes | Same week |
| **Privacy signage** (CCTV notice in the store) | Any local print shop | Get quotes; A4 acrylic signs are inexpensive | 2–3 days |
| **Data Privacy Act counsel** | A Philippine law firm with a data-privacy practice | Quote (`numbers.json` estimates PHP 150,000 once plus PHP 20,000/month) | Engagement letter; 2–4 weeks for a DPIA and opinion |
| **Accountant / bookkeeper** | Local CPA firm or freelance bookkeeper | Quote | Monthly retainer |

#### ⚠ A cost the CFO numbers are missing: the edge box in Core stores

`numbers.json` assumes **PHP 450 per store-month** for compute. That covers cloud, but **not a box in every Core store**. If each Core store needs its own edge box (about PHP 15,000, written off over 24 months ≈ **PHP 625 per store-month**):

- contribution falls from PHP 2,520 to about **PHP 1,895** per store-month (63%)
- break-even rises from 120 to about **158 paying stores** (300,000 ÷ 1,895)

**Recommendation:** charge a **one-time hardware fee of PHP 15,000 per Core store** (the chain owns the box). Then `numbers.json` stays correct and nothing changes. Pilots keep using **loaned** boxes (already in the PHP 40,000 delivery cost). Decide this before the first Core contract. If you choose to absorb the box instead, add the line to `numbers.json` and re-run `/founder-cfo`. `numbers.json` was **not** changed.

### 3. People

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

### 4. Routines (one page each)

#### SOP 1: Camera-readiness check (free, before signing)
1. Get written permission from the chain to view 1 day of footage from 2 stores.
2. Copy the footage **on-site or by secure transfer**. Never by email or chat.
3. Run the readiness script: resolution, frames per second, angle coverage of aisles and checkout.
4. Score each camera pass / fix / fail. A "fix" says exactly what to change (angle, height, lighting).
5. Delete the footage within 7 days and log the deletion.
6. Send the result email the same week (template in `brand.md`, touchpoint 2).

#### SOP 2: Pilot install day
1. Confirm the visit time with the store manager 48 hours ahead.
2. Bring the kit: edge box, power supply, UPS, switch, cables, privacy signs, checklist.
3. Put up privacy notices at every entrance **before** turning anything on.
4. Connect the edge box to the camera network (read-only stream). Never change the chain's NVR settings.
5. Test: counts appear on the dashboard within 30 minutes.
6. Brief staff: what the box does, who to call, "no faces are stored".
7. Photo of the install. Sign-off by the store manager.

#### SOP 3: The weekly pilot note and the final readout
1. Pull test vs control on the agreed KPI only.
2. Mark data gaps clearly. Never fill them silently.
3. Weeks 1–8: one page, sent Monday 10:00.
4. Week 9: the peso payback readout. If the test stores did not beat the controls, **start the refund the same day**.

#### SOP 4: Handling a complaint
1. Reply within 4 working hours: "We've got it, here is who is on it."
2. Get the facts (store, time, what happened). Check the logs.
3. Fix or explain in plain words within 2 working days.
4. For any privacy complaint, involve the Data Protection Officer at once. A suspected personal-data breach follows the NPC breach rules (notification within 72 hours where required).
5. Log it and review it at the Friday meeting.

#### SOP 5: Friday kit check and reorder
1. Count spare edge boxes, power supplies, switches and signs.
2. Keep at least **2 spare kits** at all times. Reorder boxes when spares fall to 2 (allow 3–6 weeks).
3. Check the cloud bill against budget (alert at 80%).
4. Check every edge box's last check-in time. Visit any box silent for over 24 hours.

### 5. Tools (the smallest stack)

| need | tool | published price | why |
| --- | --- | --- | --- |
| Email, docs, calendar | Google Workspace Business Starter | about **PHP 280/user/month** ([Z.com reseller page](https://web.z.com/ph/google-workspace/); check Google's own page) | Same vendor as the cloud; one login |
| Cloud | Google Cloud | pay-as-you-go | Already used by the product |
| Payments (B2B) | Bank transfer and checks with official receipts; online invoicing through the bank | bank fees (~1% in `numbers.json`) | Chains pay by transfer on terms |
| Bookkeeping | A local cloud accounting tool your accountant supports, or the accountant's own system | quote | Must produce BIR-compliant books and receipts |
| Tracker | A shared sheet or the free tier of a task tool | free | Pilots, incidents, open questions |
| CRM | A shared sheet until 30 accounts | free | Only a few hundred named buyers |

### 6. Licences, permits and insurance (checklist)

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

### 7. Risk register

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

## Launch plan

Today is **Wednesday 7 October 2026**. The hackathon submission is due **Sunday 18 October**. Public launch is **Monday 16 November 2026** (`marketing.md`). Owners: **A** = founder (product), **B** = founder (sales), **E** = engineer.

### 1. Test before you spend: three paid pilots

This is a service sold to businesses, so the test is **three paid pilots at the planned price** (PHP 75,000 each, money-back guarantee, `offer.md`). Until they are signed, **do not hire** or sign the large costs in `numbers.json` (second engineer, sales hire, coworking). The lean plan in `cfo.md` applies.

**The success line, written before the test starts:**

> From **60 named operations and merchandising heads** contacted between 2 Nov and 31 Dec 2026: at least **10 free camera checks** done and at least **3 paid pilots signed** (contract signed and 50% paid up front).

**Compare with the panel.** The simulated panel bought at **10%**, so 60 contacts "should" give about 6 pilots. The panel is an upper bound.

| real result by 31 Dec | what it means | what to do |
| --- | --- | --- |
| 3 or more pilots | The offer works with real buyers | Run them. Hire engineer 2 only after the first readout wins |
| 1–2 pilots | Some interest, trust still the blocker | Run them as case studies. Push supplier co-funding |
| 0 pilots, but 10+ camera checks | People are interested but don't believe it | Back to `/founder-offer`: smaller first step (one store, PHP 25,000?) |
| fewer than 10 camera checks | The message or the list is wrong | Back to `/founder-marketing` and `/founder-pricing` |

**Trust the real buyers over the panel.**

### 2. The countdown

Critical path tasks are marked **★**: if they slip, the launch date moves.

#### Week of 5 Oct: finish the hackathon
| task | owner | due |
| --- | --- | --- |
| ★ Final app polish, demo video, submission | A, E | Fri 16 Oct |
| Submit to AI Builder Cup | A | **Sun 18 Oct** |

#### Week of 19 Oct: name and legal
| task | owner | due |
| --- | --- | --- |
| ★ Pick the company name from the shortlist; IPOPHL and WIPO searches (`brand.md`) | A, B | Wed 21 Oct |
| Register the domain and the handles for the chosen name | B | Wed 21 Oct |
| ★ SEC name reservation and registration via eSPARC (`ops.md`) | B | start Thu 22 Oct |
| Engage Data Privacy Act counsel (quote, engagement letter) | B | Fri 23 Oct |
| Order 2 edge-box kits (3–6-week lead time) | A | Fri 23 Oct |

#### Week of 26 Oct: privacy and materials
| task | owner | due |
| --- | --- | --- |
| ★ Data-processing agreement and pilot contract templates (KPI, controls, refund rule) | B + counsel | Fri 30 Oct |
| DPIA draft for in-store camera analytics; appoint the DPO | A + counsel | Fri 30 Oct |
| Camera-readiness script and report template (SOP 1) | A, E | Fri 30 Oct |
| Landing page, one-pager and logo concept (`brand.md`) | B | Fri 30 Oct |

#### Week of 2 Nov (L-14): marketing starts
| task | owner | due |
| --- | --- | --- |
| Marketing calendar from L-14 (`marketing.md`) | B | daily |
| List of 60 named buyers; 10 warm intro requests | B | Wed 4 Nov |
| Barangay clearance and business permit applications | B | Fri 6 Nov |
| Landing page live: "Book a free camera check" | B | **Fri 6 Nov** |

#### Week of 9 Nov (L-7): soft open
| task | owner | due |
| --- | --- | --- |
| ★ **Soft open:** 2 free camera checks with friendly operators | A, B | Wed 11 Nov |
| Fix whatever the soft open breaks | A, E | Fri 13 Nov |
| BIR registration and invoices ready, so a pilot can be billed | B + accountant | Fri 13 Nov |
| Install-day kit packed and tested (SOP 2) | A | Fri 13 Nov |

#### Mon 16 Nov: launch (see run sheet)

#### After launch
| task | owner | due |
| --- | --- | --- |
| Follow-ups; book camera checks | B | daily |
| First pilot kick-off, if signed | A, B | from 30 Nov |
| Real-test review: did we hit the success line? | A, B | **Thu 31 Dec** |

### 3. Launch-day run sheet: Monday 16 November 2026

| time | who | what |
| --- | --- | --- |
| 07:30 | A | Check the landing page, the booking form and the demo app; screenshot proof |
| 08:00 | B | LinkedIn post: hook 2, "Pay only if the test stores beat the control stores." 5 design-partner slots, until 31 Mar 2027 |
| 08:30 | B | Personal messages to the 20 warmest contacts (not a mass mail) |
| 10:00 | A, B | Live short demo on LinkedIn or a recorded walkthrough: same shoppers, two layouts |
| 12:00 | B | Reply to every comment and message within the hour |
| 14:00 | B | Email the 5 FMCG trade-marketing leads (supplier co-funding, hook 8) |
| 16:00 | A, B | Count: messages sent, replies, camera checks booked |
| 17:30 | A, B | 15-minute review: what to change tomorrow |

**If something breaks** (from the risk register in `ops.md`):
- The landing page or form is down: post the founder's email and a calendar link instead.
- The demo fails live: switch to the recorded video. Never show invented numbers.
- A privacy question in public: answer with the DPA pack summary and offer a call.

The opening offer is the real one: **5 design-partner slots, ends 31 March 2027**. No fake countdowns.

### 4. The first 30 days: what to measure

| number | source | target | change if |
| --- | --- | --- | --- |
| Calls booked per week | `marketing.md` | ≥ 5 | under 3 for two weeks → new message or list |
| Camera checks done | `marketing.md` | ≥ 2 a month | under 2 → the offer isn't believed |
| Pilots signed | this plan | 3 by 31 Dec | 0 by 31 Dec → `/founder-offer` |
| Cash left / months of runway | `cfo.md` | ≥ 6 months | under 6 → stop all non-essential spend |
| Paying Core stores vs break-even | `cfo.md` | 120 (60 on the lean plan) | not expected before month 5; track from the first pilot |

**Reviews**
- **Day 7 (Mon 23 Nov):** Did the messages get replies? Which hook got the most? Any privacy or camera worries we didn't expect?
- **Day 14 (Mon 30 Nov):** How many camera checks are booked? Did any pass? What stopped the people who said no?
- **Day 30 (Wed 16 Dec):** Are we on track for 3 pilots by 31 Dec? If not, what do we change: the offer, the price, the list or the message? Decide, and write the decision down.

*The panel is simulated buyers; the numbers are projections. Real pilots decide. Not legal or financial advice.*

_The panel is simulated buyers and the numbers are projections from your inputs. Confirm demand with real customers and costs with real quotes before you spend. Not financial, legal or tax advice._
