import time
import requests
import random
import threading

def simulate_traffic():
    urls = [
        "http://localhost:5000/api/health",
        "http://localhost:5000/"
    ]
    
    print("Starting simulated traffic to API (Press Ctrl+C to stop)...")
    while True:
        target = random.choice(urls)
        try:
            response = requests.get(target, timeout=2)
            if response.status_code == 200:
                print(f"[OK] Hit {target}")
            else:
                print(f"[{response.status_code}] Hit {target}")
        except Exception as e:
            print(f"[FAIL] Could not connect: {e}")
        
        # Random sleep between highly active and low activity
        time.sleep(random.uniform(0.1, 1.5))

if __name__ == "__main__":
    # Run a few threads to simulate multiple users
    for _ in range(3):
        t = threading.Thread(target=simulate_traffic, daemon=True)
        t.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping traffic.")
