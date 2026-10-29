"""比對載具發票 CSV 與 SNShien 記帳紀錄, 找出可能漏記的發票。

用法: python reconcile.py --csv-dir <CSV 資料夾> --out <結果 JSON 路徑>

結果 JSON 欄位: start, end, invoiceCount, missing[], matched[]
每張發票: invoiceNo, date (yyyy/MM/dd), storeName, netAmount, items[{name, qty, amount}],
matched 另有 matchedBy (exact / subset)、discount ({rate, amount} 或 null)、records (命中的記帳項目)。

比對邏輯 (兩段式 ± 1 日), 逐日處理有發票的日子, 候選記帳池 = 當日與前一日、尚未被用掉的記帳:
1. 單筆精確匹配: 找一筆記帳金額恰好等於發票淨額
2. subset sum 補配: 剩下的發票依淨額由大到小, 找一組記帳金額加總恰好等於淨額
折扣商家同時嘗試原金額與折扣後金額。
"""
import argparse
import csv
import glob
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
import winreg
from datetime import datetime, timedelta

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


def reconcile(invoices, records):
    remaining = {r["_id"]: r for r in records}
    matched, missing = [], []

    def mark(inv, by, rate, amount, recs):
        for r in recs:
            del remaining[r["_id"]]
        inv.update(matchedBy=by, discount={"rate": rate, "amount": amount} if rate else None,
                   records=[{k: v for k, v in r.items() if k != "_id"} for r in recs])
        matched.append(inv)

    for day in sorted({inv["date"] for inv in invoices}):
        prev = (datetime.strptime(day, "%Y/%m/%d") - timedelta(days=1)).strftime("%Y/%m/%d")
        pool = lambda: [r for r in remaining.values() if r["date"] in (day, prev)]
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

        for inv in sorted(left, key=lambda x: -x["netAmount"]):
            for amount, rate in targets(inv):
                recs = find_subset(pool(), amount)
                if recs:
                    mark(inv, "subset", rate, amount, recs)
                    break
            else:
                missing.append(inv)

    key = lambda x: (x["date"], x["invoiceNo"])
    return sorted(matched, key=key), sorted(missing, key=key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    invoices = parse_csvs(args.csv_dir)
    start = min(inv["date"] for inv in invoices)
    end = max(inv["date"] for inv in invoices)
    # 比對池含 D-1, 起始日前一天的記帳也要抓
    fetch_start = (datetime.strptime(start, "%Y/%m/%d") - timedelta(days=1)).strftime("%Y/%m/%d")
    records = fetch_records(read_gas_url(snshien_root()), fetch_start, end)

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
