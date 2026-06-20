import os
import subprocess
import time
import webbrowser
import sys

def main():
    print("==================================================================")
    print("🚀 USV SWARM PLANNER v3.0 — Launching Automated Orchestration...")
    print("==================================================================")
    
    # Προσδιορισμός των φακέλων της εφαρμογής
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_path = os.path.join(base_dir, "frontend", "index.html")
    
    print(f"📂 Working Directory: {base_dir}")
    
    # 1. Εκκίνηση του FastAPI Backend
    print("\n🧠 [BACKEND] Starting FastAPI Engine (Uvicorn)...")
    try:
        # Χρησιμοποιούμε το ίδιο Python executable που τρέχει τώρα
        backend_process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=backend_dir
        )
    except Exception as e:
        print(f"❌ Κρίσιμο Σφάλμα κατά την εκκίνηση του backend: {e}")
        return

    # 2. Αναμονή για προετοιμασία (Φόρτωση GeoJSON & σύνδεση Port 8765)
    print("⏳ [SYSTEM] Waiting for database and GeoJSON map textures to index...")
    time.sleep(2)
    
    # 3. Αυτόματο άνοιγμα του Frontend στον Browser
    print("\n📺 [FRONTEND] Launching Mission Control Graphical Interface (UI)...")
    if os.path.exists(frontend_path):
        # Μετατροπή του τοπικού μονοπατιού σε URL μορφή για τον browser
        url = f"file://{frontend_path}"
        webbrowser.open(url)
        print("🔗 UI launched successfully via default browser.")
    else:
        print(f"❌ Σφάλμα: Το αρχείο UI δεν βρέθηκε στο: {frontend_path}")
        print("💡 Παρακαλώ ανοίξτε το αρχείο frontend/index.html χειροκίνητα.")
        
    print("\n==================================================================")
    print("🟢 SYSTEM IS ONLINE & OPERATIONAL.")
    print("🛑 Πατήστε Ctrl+C σε αυτό το παράθυρο για να κλείσετε την εφαρμογή.")
    print("==================================================================")
    
    # Κρατάμε το script ζωντανό για να μην πεθάνει η διαδικασία του backend
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 [SHUTDOWN] Λήψη σήματος τερματισμού. Κλείσιμο USV Swarm Planner...")
        backend_process.terminate()
        try:
            backend_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        print("⚡ All processes terminated cleanly. Safe to close.")

if __name__ == "__main__":
    main()