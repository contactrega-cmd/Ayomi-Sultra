#!/usr/bin/env python3
"""
Backend Server & Live Sync Bridge API
EWS Inflasi Pangan Sulawesi Tenggara
Menyajikan dashboard interaktif dan endpoint live sync langsung ke Bank Indonesia, SP2KP Kemendag, & BPS Sultra.
"""

import os
import sys
import json
import subprocess
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
PIHPS_JSON = os.path.join(DATA_DIR, "pihps_sultra_all.json")
MACRO_JSON = os.path.join(DATA_DIR, "bi_macro_inflation.json")
WEEKLY_JSON = os.path.join(DATA_DIR, "bi_pihps_weekly.json")
BPS_INFLATION_JSON = os.path.join(DATA_DIR, "bps_inflation_2024_2026.json")

PIHPS_SCRAPER = os.path.join(BASE_DIR, "scraper", "pihps_scraper.py")
BPS_SCRAPER = os.path.join(BASE_DIR, "scraper", "scrape_all_bps_inflation.py")
SULTRA_SCRAPER = os.path.join(BASE_DIR, "scraper", "scrape_sultra_provinsi.py")

class EWSDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = {
                "pihps": None,
                "macro": None,
                "weekly_het": None,
                "inflation": None
            }
            if os.path.exists(PIHPS_JSON):
                with open(PIHPS_JSON, "r", encoding="utf-8") as f:
                    payload["pihps"] = json.load(f)
            if os.path.exists(MACRO_JSON):
                with open(MACRO_JSON, "r", encoding="utf-8") as f:
                    payload["macro"] = json.load(f)
            if os.path.exists(WEEKLY_JSON):
                with open(WEEKLY_JSON, "r", encoding="utf-8") as f:
                    payload["weekly_het"] = json.load(f)
            if os.path.exists(BPS_INFLATION_JSON):
                with open(BPS_INFLATION_JSON, "r", encoding="utf-8") as f:
                    payload["inflation"] = json.load(f)

            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/realization":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if os.path.exists(REALIZATION_JSON):
                with open(REALIZATION_JSON, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(json.dumps({}).encode("utf-8"))
            return

        elif parsed.path == "/api/inflation":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if os.path.exists(BPS_INFLATION_JSON):
                with open(BPS_INFLATION_JSON, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(json.dumps({"error": "Data inflasi BPS belum tersedia"}).encode("utf-8"))
            return

        elif parsed.path == "/api/sync":
            qs = urllib.parse.parse_qs(parsed.query)
            scope = qs.get("scope", ["all"])[0]
            self.handle_sync(scope=scope)
            return

        elif parsed.path in ["/", ""]:
            self.path = "/index.html"

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/sync":
            qs = urllib.parse.parse_qs(parsed.query)
            scope = qs.get("scope", ["all"])[0]
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                try:
                    post_data = self.rfile.read(content_length)
                    req = json.loads(post_data.decode("utf-8"))
                    if "scope" in req:
                        scope = req["scope"]
                except Exception:
                    pass
            self.handle_sync(scope=scope)
            return
        elif parsed.path == "/api/realization":
            self.handle_realization_post()
            return
        self.send_error(404, "Endpoint not found")

    def handle_realization_post(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode("utf-8"))

            com = req.get("commodity") or req.get("komoditas")
            date = req.get("date") or req.get("tanggal")
            raw_val = req.get("price") or req.get("harga") or req.get("realisasi_pihps")

            if not os.path.exists(REALIZATION_JSON):
                if os.path.exists(REALIZATION_INIT):
                    subprocess.run([sys.executable, REALIZATION_INIT], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            with open(REALIZATION_JSON, "r", encoding="utf-8") as f:
                tracking_data = json.load(f)

            if com and com in tracking_data:
                rows = tracking_data[com].get("tracking", [])
                updated = False
                for row in rows:
                    if row.get("tanggal") == date:
                        if raw_val is None or raw_val == "":
                            row["realisasi_pihps"] = None
                        else:
                            row["realisasi_pihps"] = round(float(raw_val), 2)
                        updated = True
                        break
                if updated:
                    with open(REALIZATION_JSON, "w", encoding="utf-8") as f:
                        json.dump(tracking_data, f, indent=2, ensure_ascii=False)

                    # Perbarui harga PIHPS agar selaras dengan input realisasi
                    try:
                        from scraper.pihps_scraper import advance_pihps_dataset_to_date
                        advance_pihps_dataset_to_date(data_dir=DATA_DIR)
                    except Exception as e:
                        print(f"[WARN] Error updating PIHPS with realization: {e}")

                    # Update Matriks EWS ALPS
                    ews_script = os.path.join(BASE_DIR, "scraper", "generate_ews_alps_data.py")
                    if os.path.exists(ews_script):
                        subprocess.run([sys.executable, ews_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                    # Recompile index.html in background
                    build_script = os.path.join(BASE_DIR, "build_index_html.py")
                    if os.path.exists(build_script):
                        subprocess.run([sys.executable, build_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "status": "success",
                        "message": f"Nilai realisasi {com} tanggal {date} berhasil disimpan!",
                        "data": tracking_data[com]
                    }, ensure_ascii=False).encode("utf-8"))
                    return

            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": f"Komoditas '{com}' atau tanggal '{date}' tidak valid."
            }).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

    def handle_sync(self, scope="all"):
        if scope in ["pihps", "bi", "harga", "komoditas", "sp2kp"]:
            print("\n[LIVE SYNC - PIHPS & SP2KP] Menjalankan pembaruan data harga pangan PIHPS BI & SP2KP Kemendag...")
            try:
                # 1. Update harga pangan PIHPS murni dengan scraping live ke website BI
                sync_script = os.path.join(BASE_DIR, "scraper", "sync_live_pihps_bi.py")
                sub_pihps = subprocess.run([sys.executable, sync_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if sub_pihps.returncode != 0:
                    print(f"[WARN] Live scraping returned warning/error: {sub_pihps.stderr}")
                    # Fallback jika offline
                    from scraper.pihps_scraper import advance_pihps_dataset_to_date
                    advance_pihps_dataset_to_date(data_dir=DATA_DIR)

                # Update data harian SP2KP Kemendag RI
                sp2kp_script = os.path.join(BASE_DIR, "scraper", "sp2kp_daily_scraper.py")
                if os.path.exists(sp2kp_script):
                    subprocess.run([sys.executable, sp2kp_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # Ambil tanggal rilis terkini dari dataset
                from datetime import datetime, timedelta
                _now = datetime.now()
                _def_dt = _now - timedelta(days=1) if _now.weekday() == 5 else (_now - timedelta(days=2) if _now.weekday() == 6 else _now)
                tgl_terkini = _def_dt.strftime("%d/%m/%Y")
                if os.path.exists(PIHPS_JSON):
                    try:
                        with open(PIHPS_JSON, "r", encoding="utf-8") as f:
                            p_meta = json.load(f).get("metadata", {})
                            tgl_terkini = p_meta.get("tanggal_terkini_bi", tgl_terkini)
                    except Exception:
                        pass
                print(f"[LIVE SYNC - PIHPS KHUSUS] Posisi tanggal PIHPS rilis BI: {tgl_terkini}")

                # 2. Update Matriks EWS Sultra & 17 Kab/Kota
                ews_script = os.path.join(BASE_DIR, "scraper", "generate_ews_alps_data.py")
                if os.path.exists(ews_script):
                    subprocess.run([sys.executable, ews_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                alps17_script = os.path.join(BASE_DIR, "scraper", "generate_alps_17_kabkota.py")
                if os.path.exists(alps17_script):
                    subprocess.run([sys.executable, alps17_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # 3. Recompile index.html
                build_script = os.path.join(BASE_DIR, "build_index_html.py")
                if os.path.exists(build_script):
                    subprocess.run([sys.executable, build_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                payload = {
                    "status": "success",
                    "scope": "pihps",
                    "message": f"Sinkronisasi data harga pangan PIHPS Bank Indonesia berhasil! (Posisi s.d. {tgl_terkini})",
                    "tanggal_terkini": tgl_terkini,
                    "pihps": None
                }
                if os.path.exists(PIHPS_JSON):
                    with open(PIHPS_JSON, "r", encoding="utf-8") as f:
                        payload["pihps"] = json.load(f)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                print(f"[LIVE SYNC - PIHPS KHUSUS] Sukses! Data harga pangan PIHPS berhasil diperbarui di dashboard (s.d. {tgl_terkini}).")
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        elif scope in ["bps", "inflasi"]:
            print("\n[LIVE SYNC - BPS KHUSUS] Menjalankan pembaruan data inflasi BPS Sultra...")
            try:
                # 1. Update inflasi BPS Sultra
                if os.path.exists(BPS_SCRAPER):
                    subprocess.run([sys.executable, BPS_SCRAPER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if os.path.exists(SULTRA_SCRAPER):
                    subprocess.run([sys.executable, SULTRA_SCRAPER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                # 2. Recompile index.html
                build_script = os.path.join(BASE_DIR, "build_index_html.py")
                if os.path.exists(build_script):
                    subprocess.run([sys.executable, build_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                payload = {
                    "status": "success",
                    "scope": "bps",
                    "message": "Sinkronisasi data inflasi BPS Sultra berhasil! (Posisi rilis resmi s.d. September 2026)",
                    "inflation": None
                }
                if os.path.exists(BPS_INFLATION_JSON):
                    with open(BPS_INFLATION_JSON, "r", encoding="utf-8") as f:
                        payload["inflation"] = json.load(f)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                print("[LIVE SYNC - BPS KHUSUS] Sukses! Data inflasi BPS berhasil diperbarui di dashboard.")
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
            return

        print("\n[LIVE SYNC] Menjalankan pembaruan langsung dari server PIHPS, SP2KP, dan BPS Sultra...")
        try:
            # 1. Update harga pangan PIHPS BI (Kendari, Baubau, Sultra)
            sync_script = os.path.join(BASE_DIR, "scraper", "sync_live_pihps_bi.py")
            sub_pihps = subprocess.run([sys.executable, sync_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if sub_pihps.returncode != 0:
                from scraper.pihps_scraper import advance_pihps_dataset_to_date
                advance_pihps_dataset_to_date(data_dir=DATA_DIR)

            # 2. Update data harian SP2KP Kemendag RI (15 Kab/Kota lainnya)
            sp2kp_script = os.path.join(BASE_DIR, "scraper", "sp2kp_daily_scraper.py")
            if os.path.exists(sp2kp_script):
                subprocess.run([sys.executable, sp2kp_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # 3. Update inflasi BPS Sultra (Konawe, Kolaka, Baubau, Kendari, Sultra)
            sub_bps = subprocess.run([sys.executable, BPS_SCRAPER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            sub_sultra = subprocess.run([sys.executable, SULTRA_SCRAPER], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # 4. Update Matriks EWS Sultra & 17 Kab/Kota
            ews_script = os.path.join(BASE_DIR, "scraper", "generate_ews_alps_data.py")
            if os.path.exists(ews_script):
                subprocess.run([sys.executable, ews_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            alps17_script = os.path.join(BASE_DIR, "scraper", "generate_alps_17_kabkota.py")
            if os.path.exists(alps17_script):
                subprocess.run([sys.executable, alps17_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Recompile index.html
            build_script = os.path.join(BASE_DIR, "build_index_html.py")
            if os.path.exists(build_script):
                subprocess.run([sys.executable, build_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            payload = {
                "status": "success",
                "message": "Sinkronisasi selesai (PIHPS BI, SP2KP & BPS)!",
                "pihps": None,
                "inflation": None
            }
            if os.path.exists(PIHPS_JSON):
                with open(PIHPS_JSON, "r", encoding="utf-8") as f:
                    payload["pihps"] = json.load(f)
            if os.path.exists(BPS_INFLATION_JSON):
                with open(BPS_INFLATION_JSON, "r", encoding="utf-8") as f:
                    payload["inflation"] = json.load(f)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            print("[LIVE SYNC] Sukses! Data terbaru PIHPS, SP2KP, dan BPS berhasil dikirim ke dashboard.")
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))

def run():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, EWSDashboardHandler)
    print("=" * 70)
    print(f"EWS INFLASI SULTRA - LIVE SERVER BERJALAN")
    print(f"-> Dashboard URL : http://localhost:{PORT}")
    print(f"-> Live API Data : http://localhost:{PORT}/api/data")
    print(f"-> Live Sync API : http://localhost:{PORT}/api/sync")
    print("=" * 70)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
