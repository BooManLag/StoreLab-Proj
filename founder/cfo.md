# CFO's note: StoreLab

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

# Unit economics: StoreLab (per-store SaaS for Philippine convenience chains; all amounts in PHP; ESTIMATES, see cfo-sources.md)

Every number below comes from the input file. Nothing is looked up or guessed.

## One store-month

| line | per store-month |
| --- | ---: |
| Price | $3,000.00 |
| Cloud compute, video processing, storage, Gemini calls (estimate) | -$450.00 |
| Payment / bank fees ~1% (estimate) | -$30.00 |
| **Contribution** (what each store-month leaves to pay the fixed costs) | **$2,520.00** (84%) |

## The margin that matters

Fixed costs: $300,000 a month (2 engineers (estimate PHP 90k each) $180,000, 1 sales & customer success (estimate) $60,000, Base cloud, tools, software (estimate) $25,000, Legal / data-privacy retainer (estimate) $20,000, Coworking desk (estimate) $15,000).

- **Break-even: 120 store-months a day.** Below that you lose money every month.
- **Profit margin at your plan** (150 a day): **17%** of every sale, after every cost.

## Year 1, month by month

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

## What if

| scenario | margin at plan | break-even a day | year 1 profit |
| --- | ---: | ---: | ---: |
| Base plan | 17% | 120 | -$2,995,200 |
| Price -10% | 8% | 136 | -$3,067,200 |
| Volume -20% | 1% | 120 | -$3,116,160 |
| Unit costs +15% | 15% | 123 | -$3,012,480 |

## Red flags

- Year 1 loses money on operations (-$2,995,200).
- The startup spend is not earned back within year 1.
