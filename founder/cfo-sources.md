# Where the CFO numbers come from

Every input in `numbers.json` and `pilot-numbers.json` is an **estimate made by Claude**, with the reasoning below. No quote, invoice or published price list has been used yet. Replace each one with a real figure, then re-run `/founder-cfo`.

| input | value (PHP) | basis | status |
| --- | --- | --- | --- |
| Price per store-month | 3,000 | `pricing.md`: the panel's indifference point (PHP 3,008) | from the panel (simulated) |
| Cloud, video processing, storage, Gemini per store-month | 450 | rough sizing: one store's camera stream at low frame rate, plus small Gemini usage per experiment | **estimate**. Get a Google Cloud pricing-calculator quote |
| Payment / bank fees | 30 | about 1% of PHP 3,000 for bank transfer or invoicing | **estimate** |
| 2 engineers | 180,000/month | about PHP 90,000 each for senior developers in Metro Manila | **estimate**. Use your actual pay |
| Sales & customer success | 60,000/month | one hire | **estimate** |
| Base cloud and tools | 25,000/month | environments, monitoring, workspace software | **estimate** |
| Legal / data-privacy retainer | 20,000/month | small-firm retainer | **estimate**. Get a quote |
| Coworking | 15,000/month | a few desks | **estimate** |
| Registration and permits | 50,000 one-off | SEC, BIR, LGU permits | **estimate**. See `ops.md` |
| Data Privacy Act opinion and impact assessment | 150,000 one-off | counsel opinion plus a privacy impact assessment | **estimate**. Get a quote |
| Pilot field kit and travel | 150,000 one-off | edge box or mini-PC, network gear, travel to first sites | **estimate** |
| Website and sales materials | 50,000 one-off | | **estimate** |
| Pilot delivery cost | 40,000 per pilot | about 2 weeks of an analyst, travel, cloud | **estimate** |
| Pilot refund claim rate | 30% | the simulator is unproven on real stores, so this is set conservatively | **assumption** |
| Ramp | 0,0,0,0,10,10,20,20,30,40,50,60 stores | pilots in months 1–4; conversions from month 5 at about 10–15 stores per chain; kept below the panel's 10% (simulated) buy rate | **assumption** |
