"""
Entry Point: Mode Server Web Browser (FTTH Network Planner)
Menjalankan server FastAPI via Uvicorn.
Buka browser dan akses: http://localhost:8000
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("Memulai FTTH Network Planner (Web Server Edition)")
    print("Akses aplikasi melalui browser di: http://127.0.0.1:8000")
    print("Dokumentasi REST API Swagger di : http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "ftth_web.backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
