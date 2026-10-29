"""從財政部電子發票平台下載手機條碼載具的消費明細 CSV。

用法: python fetch_invoices.py --start 2026/09/01 --end 2026/10/29 --out <資料夾> [--accounts 1,2]

帳密從 User 環境變數讀: INVOICE_ACC{n}_PHONE / INVOICE_ACC{n}_PWD。
不給 --accounts 時從 1 開始往上找, 遇到第一個沒設定的編號就停。
登入需要人工輸入圖形驗證碼: 腳本會開 Edge 視窗並填好帳密, 使用者輸入驗證碼按登入後, 其餘自動完成。
平台限制每次查詢區間須在同一個月內, 跨月會自動拆成多次查詢。
"""
import argparse
import io
import json
import os
import sys
import winreg
from datetime import date, datetime, timedelta

from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

LOGIN_URL = "https://www.einvoice.nat.gov.tw/accounts/login/mw"
SEARCH_URL = "https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search"
PROFILE_DIR = os.path.join(os.environ["LOCALAPPDATA"], "shien-invoice-check", "profile")
LOGIN_TIMEOUT_SEC = 300  # 人工輸入驗證碼的等待上限; 留給使用者切回 Edge 視窗的時間, 逾時就略過該帳號而不是無限等


def user_env(name):
    # 新設的 User 環境變數不會出現在已啟動的行程裡, 直接讀登錄檔
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except FileNotFoundError:
        return os.environ.get(name)


def month_chunks(start, end):
    chunks = []
    cur = start
    while cur <= end:
        next_month = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        chunk_end = min(end, next_month - timedelta(days=1))
        chunks.append((cur, chunk_end))
        cur = next_month
    return chunks


def to_utc_iso(d, end_of_day):
    # 平台以台灣時間 (UTC+8) 解讀日期
    local = datetime(d.year, d.month, d.day, 23, 59, 59) if end_of_day else datetime(d.year, d.month, d.day)
    return (local - timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def login(page, phone, pwd):
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#mobile_phone", timeout=120000)  # 期間可能要先過 Cloudflare 驗證
    page.fill("#mobile_phone", phone)
    page.fill("#password", pwd)
    page.focus("#captcha")
    print(f"  請在 Edge 視窗輸入圖形驗證碼並按登入 (限 {LOGIN_TIMEOUT_SEC // 60} 分鐘)")
    for _ in range(LOGIN_TIMEOUT_SEC):
        page.wait_for_timeout(1000)
        if "/accounts/login" not in page.url:
            # 登入後還有一串 SSO 轉址, 沒走完就切頁會被打斷
            page.wait_for_url("**/portal/**", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=60000)
            return True
    return False


def download_range(page, start, end, out_dir, prefix):
    rng = {"start": to_utc_iso(start, False), "end": to_utc_iso(end, True)}

    # 直接改寫查詢請求的日期, 不操作網頁上的日期選擇器
    def rewrite(route):
        body = json.loads(route.request.post_data)
        body["searchStartDate"], body["searchEndDate"] = rng["start"], rng["end"]
        route.continue_(post_data=json.dumps(body))

    page.route("**/btc502w/getSearchCarrierInvoiceListJWT", rewrite)
    try:
        query_btn = page.get_by_role("button", name="查詢", exact=True)
        for attempt in range(2):
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            try:
                query_btn.wait_for(timeout=30000)
                break
            except Exception:
                if attempt == 1:
                    page.screenshot(path=os.path.join(out_dir, f"{prefix}_error.png"), full_page=True)
                    raise RuntimeError(f"查詢頁沒出現查詢按鈕, 目前網址 {page.url}, 截圖存在 {prefix}_error.png")
        query_btn.click()
        page.wait_for_url("**/btc502w/detail", timeout=60000)
        page.wait_for_timeout(3000)
    finally:
        page.unroute("**/btc502w/getSearchCarrierInvoiceListJWT")

    if page.query_selector("#invoiceDetailAll") is None:
        print(f"  {start:%Y/%m/%d}~{end:%Y/%m/%d}: 查無發票")
        return []

    # 每頁筆數要選完再按旁邊的「執行」才生效; 沒生效也只是多翻幾頁
    # 頁面上另有兩組明細彈窗的分頁控制共用同 id, 第一組才是主列表
    page.locator("#SelectSizes").first.select_option("100")
    page.locator("#SelectSizes + button").first.click()
    page.wait_for_timeout(3000)

    saved = []
    page_no = 1
    while True:
        page.check("#invoiceDetailAll", force=True)
        page.wait_for_timeout(1000)
        with page.expect_download(timeout=120000) as dl:
            page.get_by_role("button", name="下載CSV檔").click(timeout=30000)
        path = os.path.join(out_dir, f"{prefix}_{start:%Y%m%d}_{end:%Y%m%d}_p{page_no}.csv")
        dl.value.save_as(path)
        saved.append(path)
        print(f"  已下載 {os.path.basename(path)}")

        next_btn = page.query_selector("a.page-link[title='下一頁']")
        if next_btn is None or next_btn.get_attribute("disabled") is not None:
            break
        next_btn.click()
        page.wait_for_timeout(3000)
        page_no += 1
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="YYYY/MM/DD")
    ap.add_argument("--end", required=True, help="YYYY/MM/DD")
    ap.add_argument("--out", required=True)
    ap.add_argument("--accounts", help="逗號分隔的帳號編號, 預設為所有已設定的帳號")
    args = ap.parse_args()

    if args.accounts:
        accounts = args.accounts.split(",")
    else:
        accounts = []
        while user_env(f"INVOICE_ACC{len(accounts) + 1}_PHONE"):
            accounts.append(str(len(accounts) + 1))
        if not accounts:
            print("找不到任何帳號: 請設定 User 環境變數 INVOICE_ACC1_PHONE / INVOICE_ACC1_PWD")
            sys.exit(1)

    start = datetime.strptime(args.start, "%Y/%m/%d").date()
    end = min(datetime.strptime(args.end, "%Y/%m/%d").date(), date.today())
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(PROFILE_DIR, exist_ok=True)

    failed = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE_DIR, channel="msedge", headless=False, accept_downloads=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        for n in accounts:
            phone, pwd = user_env(f"INVOICE_ACC{n}_PHONE"), user_env(f"INVOICE_ACC{n}_PWD")
            if not phone or not pwd:
                print(f"帳號{n}: 環境變數 INVOICE_ACC{n}_PHONE / INVOICE_ACC{n}_PWD 未設定, 略過")
                failed.append(n)
                continue
            print(f"帳號{n} ({phone[-3:]}):")
            ctx.clear_cookies()  # 確保不沿用上一組帳號的登入狀態
            if not login(page, phone, pwd):
                print(f"  登入逾時, 略過帳號{n}")
                failed.append(n)
                continue
            for s, e in month_chunks(start, end):
                download_range(page, s, e, args.out, f"acc{n}")
        try:
            ctx.close()
        except Exception:
            pass  # 使用者先手動關掉 Edge 視窗時會丟例外, 檔案已存好不影響

    print("完成" if not failed else f"完成, 但帳號 {','.join(failed)} 未下載")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
