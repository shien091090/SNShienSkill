"""比對載具發票 CSV 與 SNShien 記帳紀錄, 找出可能漏記的發票。

用法: python reconcile.py --csv-dir <CSV 資料夾> --out <結果 JSON 路徑>

結果 JSON 欄位: start, end, invoiceCount, missing[], matched[]
每張發票: invoiceNo, date (yyyy/MM/dd), storeName, netAmount, items[{name, qty, amount}],
matched 另有 matchedBy (exact / subset / group / crossday-exact / crossday-group)、discount ({rate, amount} 或 null)、records (命中的記帳項目),
group 另有 groupTotal (同店合計金額)。

比對範圍 = 對帳區間 (資料夾名稱 YYYYMMDD_YYYYMMDD; 不是這種格式就用發票的最早~最晚日期), 只抓區間內的記帳。
第一輪逐日處理有發票的日子, 候選記帳池 = 同一天、尚未被用掉的記帳:
1. 單筆精確匹配: 找一筆記帳金額恰好等於發票淨額
2. subset sum 補配: 剩下的發票依淨額由大到小, 找一組記帳金額加總恰好等於淨額
3. 同店合記: 仍未對到、同日同一家店的多張發票, 加總恰好等於一筆記帳
第二輪 (跨日): 第一輪都對不到的發票, 在整個區間剩下的記帳裡找單筆同金額, 再找同店合記, 都取日期最接近的;
命中的 matchedBy 加 "crossday" 前綴 (crossday-exact / crossday-group)。跨日不做 subset sum, 整月湊加總太容易湊出不相干的帳。
折扣商家在單筆與 subset 同時嘗試原金額與折扣後金額。
"""
import argparse
import csv
import glob
import io
import itertools
import json
import math
import os
import sys
import urllib.parse
import urllib.request
import winreg
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

# 與店家有固定折扣協議, 記帳記的是折扣後金額, 發票是原價
DISCOUNT_VENDORS = [("新知喬股份有限公司", 0.95)]

# CSV 欄位 (0-based)
COL_CARRIER, COL_DATE, COL_NO, COL_STORE, COL_QTY, COL_AMOUNT, COL_NAME = 0, 1, 2, 7, 10, 12, 13


def fail(msg):
    print(f"錯誤: {msg}")
    sys.exit(1)


def snshien_root():
    root = os.environ.get("SNSHIEN_ROOT")
    if not root:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                root = winreg.QueryValueEx(k, "SNSHIEN_ROOT")[0]
        except FileNotFoundError:
            pass
    if not root or not os.path.isdir(root):
        fail("找不到 SNShien 專案根目錄, 請設定 User 環境變數 SNSHIEN_ROOT")
    return root


def read_gas_url(root):
    path = os.path.join(root, "linebot_liveManagerIntegration", "settings.py")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        fail(f"讀不到 {path}")
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("URL_GAS_API") and "'" in s:
            return s.split("'")[1]
    fail("無法從 settings.py 讀取 URL_GAS_API")


def js_round(x):
    # 與原本 JS 版 Math.round 一致 (四捨五入), Python 的 round 是銀行家捨入
    return math.floor(x + 0.5)


def parse_csvs(csv_dir):
    files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    if not files:
        fail(f"資料夾中找不到 CSV 檔案: {csv_dir}")
    invoices = {}
    seen_in_file = {}
    for f in files:
        with open(f, encoding="utf-8-sig", newline="") as fh:
            for row in csv.reader(fh):
                if len(row) <= COL_NAME or row[COL_CARRIER] != "手機條碼":
                    continue  # 標題列與頁尾說明
                no = row[COL_NO]
                # 同一張發票可能在多個 CSV 重複出現 (分頁/兩組帳號), 只採第一個檔案的明細
                if seen_in_file.setdefault(no, f) != f:
                    continue
                inv = invoices.setdefault(no, {
                    "invoiceNo": no,
                    "date": datetime.strptime(row[COL_DATE], "%Y%m%d").strftime("%Y/%m/%d"),
                    "storeName": row[COL_STORE],
                    "netAmount": 0,
                    "items": [],
                })
                amount = float(row[COL_AMOUNT] or 0)
                inv["netAmount"] += amount
                inv["items"].append({"name": row[COL_NAME], "qty": row[COL_QTY], "amount": amount})
    result = []
    for inv in invoices.values():
        inv["netAmount"] = js_round(inv["netAmount"])
        if inv["netAmount"] > 0:
            result.append(inv)
    if not result:
        fail("CSV 中沒有淨額大於 0 的發票")
    return result


def fetch_records(gas_url, start, end):
    qs = urllib.parse.urlencode({"action": "action_get_accounting_items", "startDate": start, "endDate": end}, safe="/")
    try:
        with urllib.request.urlopen(f"{gas_url}?{qs}", timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        fail(f"呼叫 GAS API 失敗: {e}")
    if body.get("statusCode") != 200:
        fail(f"GAS API 回傳錯誤: {str(body)[:300]}")
    records = json.loads(body["responseMsg"])
    for i, rec in enumerate(records):
        rec["_id"] = i
    return records


def discount_of(store):
    for name, rate in DISCOUNT_VENDORS:
        if name in store:
            return rate
    return None


def targets(inv):
    t = [(inv["netAmount"], None)]
    rate = discount_of(inv["storeName"])
    if rate:
        t.append((js_round(inv["netAmount"] * rate), rate))
    return t


def find_subset(pool, target):
    items = [r for r in pool if r["prize"] > 0]

    def walk(i, remain, picked):
        if remain == 0:
            return picked
        if i >= len(items) or remain < 0:
            return None
        return walk(i + 1, remain - items[i]["prize"], picked + [items[i]]) or walk(i + 1, remain, picked)

    return walk(0, target, [])


def group_subsets(group):
    # 兩張以上的組合, 張數多的先試; 同店同日未比對的發票通常只有幾張, 組合數很小
    for size in range(len(group), 1, -1):
        yield from itertools.combinations(group, size)


def reconcile(invoices, records):
    remaining = {r["_id"]: r for r in records}
    matched, missing = [], []

    def strip(r):
        return {k: v for k, v in r.items() if k != "_id"}

    def mark(inv, by, rate, amount, recs):
        for r in recs:
            del remaining[r["_id"]]
        inv.update(matchedBy=by, discount={"rate": rate, "amount": amount} if rate else None,
                   records=[strip(r) for r in recs])
        matched.append(inv)

    def mark_group(invs, by, hit, total, left):
        del remaining[hit["_id"]]
        for inv in invs:
            inv.update(matchedBy=by, discount=None, groupTotal=total, records=[strip(hit)])
            matched.append(inv)
            left.remove(inv)

    def by_store(invs):
        groups = {}
        for inv in invs:
            groups.setdefault(inv["storeName"], []).append(inv)
        return groups.values()

    # 第一輪: 同日
    for day in sorted({inv["date"] for inv in invoices}):
        pool = lambda: [r for r in remaining.values() if r["date"] == day]
        todo = [inv for inv in invoices if inv["date"] == day]

        left = []
        for inv in todo:
            hit = None
            for amount, rate in targets(inv):
                hit = next((r for r in pool() if r["prize"] == amount), None)
                if hit:
                    mark(inv, "exact", rate, amount, [hit])
                    break
            if not hit:
                left.append(inv)

        day_missing = []
        for inv in sorted(left, key=lambda x: -x["netAmount"]):
            for amount, rate in targets(inv):
                recs = find_subset(pool(), amount)
                if recs:
                    mark(inv, "subset", rate, amount, recs)
                    break
            else:
                day_missing.append(inv)

        # 同店多張發票合記成一筆: 只在同一家店內湊, 跨店湊容易把不相干的帳配在一起
        for group in by_store(day_missing):
            for invs in group_subsets(group):
                total = sum(i["netAmount"] for i in invs)
                hit = next((r for r in pool() if r["prize"] == total), None)
                if hit:
                    mark_group(invs, "group", hit, total, day_missing)
                    break
        missing.extend(day_missing)

    # 第二輪: 跨日, 區間內任何一天, 日期最接近的優先; 大額先配, 小額同金額的記帳多, 較不會搶錯
    to_date = lambda s: datetime.strptime(s[:10].replace("-", "/"), "%Y/%m/%d")

    def nearest(inv, amount):
        d = to_date(inv["date"])
        cands = [r for r in remaining.values() if r["prize"] == amount]
        return min(cands, key=lambda r: abs((to_date(r["date"]) - d).days), default=None)

    for inv in sorted(list(missing), key=lambda x: -x["netAmount"]):
        for amount, rate in targets(inv):
            hit = nearest(inv, amount)
            if hit:
                mark(inv, "crossday-exact", rate, amount, [hit])
                missing.remove(inv)
                break

    for group in by_store(missing):
        if len(group) < 2:
            continue
        for invs in group_subsets(group):
            total = sum(i["netAmount"] for i in invs)
            hit = nearest(invs[0], total)
            if hit:
                mark_group(invs, "crossday-group", hit, total, missing)
                break

    key = lambda x: (x["date"], x["invoiceNo"])
    return sorted(matched, key=key), sorted(missing, key=key)


def period_of(csv_dir, invoices):
    # 資料夾名稱就是使用者要求的對帳區間, 例如 20261101_20261130
    name = os.path.basename(os.path.normpath(csv_dir))
    try:
        a, b = name.split("_")
        return (datetime.strptime(a, "%Y%m%d").strftime("%Y/%m/%d"),
                datetime.strptime(b, "%Y%m%d").strftime("%Y/%m/%d"))
    except ValueError:
        return min(inv["date"] for inv in invoices), max(inv["date"] for inv in invoices)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    invoices = parse_csvs(args.csv_dir)
    start, end = period_of(args.csv_dir, invoices)
    invoices = [inv for inv in invoices if start <= inv["date"] <= end]
    records = fetch_records(read_gas_url(snshien_root()), start, end)

    matched, missing = reconcile(invoices, records)
    result = {"start": start, "end": end, "invoiceCount": len(invoices), "missing": missing, "matched": matched}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    print(f"{start} ~ {end}: 發票 {len(invoices)} 張, 已比對 {len(matched)}, 可能漏記 {len(missing)}")
    for inv in missing:
        print(f"  漏記? {inv['date']} {inv['storeName']} {inv['invoiceNo']} ${inv['netAmount']}")
    print(f"結果: {args.out}")


if __name__ == "__main__":
    main()
