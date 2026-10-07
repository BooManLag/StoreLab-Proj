# The offer: StoreLab "8-Week Store Test"

Built with the Offers lens (`founder-board/lenses.md`, a summary of a published framework, not anyone's words). Amounts are in PHP. Costs are estimates from `numbers.json` and `pilot-numbers.json`.

## 1. The problem list, in the buyer's words (from the panel and the competitor research)

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

## 2. Solutions, scored (value to buyer 1–5 / cost to deliver 1–5)

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

## 3. The stack

**Name: the 8-Week Store Test.** It names the result and the time, not the company.

- **Core:** *"Find out in 8 weeks whether a store change sells more, before you roll it out to the chain."* You give StoreLab one goal. It recommends the change, simulates it on your store's data, and runs it in 2–3 test stores against matched control stores. You get the real result in pesos.
- **Bonus 1: Camera-readiness check, free, before you sign** (kills "our CCTV is old").
- **Bonus 2: Data Privacy Act pack** (kills "is this allowed?").
- **Bonus 3: Endcap value report**, which you can use to price the endcaps your suppliers pay for (turns "suppliers decide" into extra supplier income).
- **Guarantee:** if the test stores don't beat the control stores on the agreed KPI, the full PHP 75,000 fee is refunded.
- **Price:** **PHP 75,000** for the 8-Week Store Test. If you continue, the full fee is credited against your first 6 months of Core (PHP 3,000/store/month, month-to-month).
- **Real scarcity:** **5 design-partner slots**, because one team can run about five pilots at once. Offer ends 31 March 2027.

### What the guarantee costs (CFO tool, `pilot-numbers.json`)

| claim rate | contribution per pilot |
| --- | --- |
| 30% (planning estimate) | **PHP 11,750** (16%) |
| 50% | **−PHP 3,250** (−4%) |

The guarantee is affordable while fewer than about **46%** of pilots claim the refund (PHP 34,250 margin before refunds ÷ PHP 75,000). The first pilot is a door-opener, not a profit centre. The money is in Core: 10 stores × PHP 2,520 contribution × 12 months ≈ PHP 302,400 a year per chain (`numbers.json`). If more than 2 of the first 5 pilots claim the refund, stop and fix the simulator before selling more.

## 4. Value equation, before (v1 pitch) → after (8-Week Store Test), 1–10

| element | before | after | what moved it |
| --- | :---: | :---: | --- |
| Dream outcome | 6 | 7 | Peso payback readout and endcap income |
| Perceived likelihood | 2 | 6 | Guarantee, readiness check, test against real control stores |
| Time to result | 3 | 7 | "8 weeks", instead of an open-ended 12-month contract |
| Effort and sacrifice | 3 | 7 | No lock-in, zero IT effort, Data Privacy Act pack, StoreLab picks the controls |

## 5. Re-test on the same 20 buyers (seed 7, `--quick`)

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
