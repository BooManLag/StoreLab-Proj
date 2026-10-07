# Competitors: StoreLab

Researched 2026-10-07 from public sources only. Where a page could not be read, it is marked. Full rows are in `competitors.csv`.

## 1. Who is there, from most direct to least

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

## 2. Price range for the comparable item

**No direct competitor publishes a price**, so there is no honest lowest, median or highest. The only figure found is a third-party estimate for RetailNext: ~USD 100–250 per sensor per month plus ~USD 500 per sensor to install ([source](https://www.ki-syndikat.de/tools/retailnext/)). A store has at least one sensor per entrance, so this is a lower bound per store. `/founder-pricing` should treat it as an anchor to check, not a fact.

## 3. Positioning map (text)

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

## 4. What their customers complain about (thin)

| theme | evidence | status |
| --- | --- | --- |
| Price of hardware plus subscription | A G2 review snippet in search results described RetailNext as very expensive, with "expensive cameras and an expensive software subscription". The page itself returned 403, so the quote is **not verified** ([G2](https://www.g2.com/products/retailnext/reviews)) | **thin**: one review, unverified |
| Lag when switching between many locations | Same G2 snippet, unverified | **thin** |
| Pricing that scales by entrances, even if you use one module | Stated by Spot AI, **a competitor** ([page](https://www.spot.ai/compare/limitations/retailnext-limitations)) | **thin**: competitor's claim |
| No public reviews at all | RetailNext has 0 reviews on [Software Advice](https://www.softwareadvice.com/product/549416-RetailNext/) | — |

Honest result: public complaint data for this B2B category is almost empty. Real objections have to come from conversations with buyers (`/founder-consumer` for simulated ones, then real interviews).

## 5. The gap

- **What exists:** measurement tools (counts, paths, heatmaps), some running on existing CCTV (Agrex, VIGI). **Physical** pilot testing (RetailNext). **Online** virtual-store research with human panels (InContext, which claims a "96%" correlation with in-store results).
- **What nobody in the sources does:** take a store's own camera and POS data, let a manager state a goal and constraints in plain language, design the change, pre-screen it against that store's own behaviour, and hand over a sized test-vs-control pilot plan. All without new hardware, and sold to Philippine convenience chains.
- **Where the gap is weak:** InContext already sells "predict before you change", and it claims high accuracy. Agrex already sells "existing CCTV, under 10 days to go live". So StoreLab's gap is the **combination**, plus the local market, not any single feature. That is real but narrow, and only a real pilot that shows the simulator works will make it believable.
- **Market note:** the two biggest Philippine chains are well above the board's "20–500 stores" segment: 7-Eleven ~4,575 stores ([Philstar, 2026](https://www.philstar.com/business/2026/04/14/2520738/despite-middle-east-crisis-7-eleven-track-5000th-store/amp/)) and Alfamart 2,337 ([Context.ph](https://context.ph/2026/05/14/7-eleven-pushes-toward-5000-store-mark-nationwide/)). The mid-size targets are the chains below them (names seen in search results include Ministop, Uncle John's, Dali, O!Save and Lawson; their store counts were not verified). `/founder-consumer` should model those buyers.

## 6. The threat: who could copy this fastest

1. **RetailNext.** It already has paths, POS correlation, pilot testing and offices in the region. A simulation step on top of its own data is a natural extension.
2. **Agrex AI.** It already runs on existing CCTV. Adding an experiment layer is a shorter step for it than building camera ingestion is for StoreLab.
3. **InContext Solutions.** It already sells prediction before change. Adding store-specific camera data would close the "existing cameras" half of the gap.

StoreLab's defence is speed into one local segment, and building up real pilot results that copycats don't have.

## Added during `/founder-brand` (2026-10-07): a same-name competitor

- **StoreLab™ (Australia, Brookvale NSW)** describes itself as "a global leader in VR simulation, focus group and research", whose software "put[s] powerful shopper marketing ideas into a 'life-like' virtual store, with planogramming, analytics and instant trade presentation" ([search-result listing](https://thedirectory.thevrara.com/organization/4684); the page itself failed its TLS check, so this is from the search summary, **not verified**). It is a **direct competitor using the same name and claiming a trademark (™)**: see `brand.md`.
- A separate **StoreLab** (UK, founded 2020) sells a Shopify mobile-app builder ([Shopify App Store](https://apps.shopify.com/storelab?locale=it), [CB Insights](https://www.cbinsights.com/compare/storelab-vs-tapcart)). It is a different category, but adds to name confusion.
