"""Export the synthetic demo dataset in the spec's data model (§10) as CSV.

    python -m storelab.export --out exports/

The CSVs load straight into BigQuery with deploy/load_bigquery.sh.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Iterable

from .store import CATEGORY_LABELS
from .world import World, get_world

TABLES = ("stores", "zones", "products", "journey_events", "transactions")


def rows(world: World, table: str) -> tuple[list[str], Iterable[list]]:
    s, h = world.store, world.history
    if table == "stores":
        head = ["store_id", "name", "region", "currency", "timezone", "floorplan_url", "width_m", "depth_m"]
        return head, [[s.store_id, s.name, s.region, s.currency, s.timezone, "/api/store", s.width, s.height]]
    if table == "zones":
        head = ["zone_id", "store_id", "name", "category", "polygon", "movable", "kind"]
        slot_cat = h.layout.slot_category()
        out = []
        for zid, rect in s.zone_rects().items():
            x0, y0, x1, y1 = rect
            poly = json.dumps([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
            is_aisle = zid.startswith("aisle")
            movable = is_aisle and not s.aisle(zid).refrigerated
            out.append([zid, s.store_id, s.aisle(zid).label if is_aisle else zid.capitalize(),
                        slot_cat.get(zid, ""), poly, movable, "aisle" if is_aisle else "area"])
        for d in s.displays:
            x0, y0, x1, y1 = d.rect
            out.append([d.id, s.store_id, d.label, h.layout.display_map.get(d.id, ""),
                        json.dumps([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), not d.restricted, f"display_{d.kind}"])
        return head, out
    if table == "products":
        head = ["sku", "name", "category", "price", "margin", "current_zone", "promotion"]
        cat_slot = h.layout.cat_slot
        promo = set(h.layout.display_map.values())
        return head, [[p.sku, p.name, p.category, p.price, p.margin, cat_slot[p.category], p.category in promo]
                      for p in s.products]
    if table == "journey_events":
        head = ["anonymous_track_id", "timestamp", "store_id", "zone_id", "x", "y", "event_type", "dwell_seconds"]

        def gen():
            for i, z, t0, t1, x, y in zip(h.ze_track.tolist(), h.ze_zone, h.ze_enter.tolist(), h.ze_exit.tolist(),
                                          h.ze_x.tolist(), h.ze_y.tolist()):
                yield [h.track_id[i], h.timestamp(h.day[i], t0), s.store_id, z, round(x, 2), round(y, 2),
                       "zone_visit", round(t1 - t0, 1)]
            for i, slot, t, eng in zip(h.de_track.tolist(), h.de_slot, h.de_time.tolist(), h.de_engaged.tolist()):
                d = s.display(slot)
                cx, cy = (d.rect[0] + d.rect[2]) / 2, (d.rect[1] + d.rect[3]) / 2
                yield [h.track_id[i], h.timestamp(h.day[i], t), s.store_id, slot, round(cx, 2), round(cy, 2),
                       "display_interaction" if eng else "display_pass", ""]
        return head, gen()
    if table == "transactions":
        head = ["transaction_id", "store_id", "timestamp", "sku", "category", "quantity", "price", "revenue", "discount"]

        def gen():
            for row, sku, cat, q, price, rev, disc in zip(h.tl_tx.tolist(), h.tl_sku, h.tl_category, h.tl_qty.tolist(),
                                                          h.tl_price.tolist(), h.tl_revenue.tolist(),
                                                          h.tl_discount.tolist()):
                yield [h.tx_id[row], s.store_id, h.timestamp(h.tx_day[row], h.tx_time[row]), sku, cat, q, price, rev, disc]
        return head, gen()
    raise KeyError(table)


def to_csv(world: World, table: str) -> str:
    head, body = rows(world, table)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(head)
    w.writerows(body)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser(description="Export the StoreLab synthetic dataset as CSV")
    ap.add_argument("--out", default="exports", help="output directory")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    world = get_world()
    for t in TABLES:
        (out / f"{t}.csv").write_text(to_csv(world, t), encoding="utf-8")
        print(f"wrote {out / (t + '.csv')}")
    print("Categories:", ", ".join(CATEGORY_LABELS.values()), "| all data is SYNTHETIC demo data")


if __name__ == "__main__":
    main()
