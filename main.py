from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


@app.get("/")
def root():
    return {"status": "running"}

@app.get("/api/flights")
def get_flights():
    statement_time = """SELECT id, opensky_timestamp
                    FROM state_snapshots
                    ORDER BY id DESC
                    LIMIT 1;"""
    statement_data= """SELECT 
                    a.icao24,
                    a.callsign,
                    a.latitude,
                    a.longitude,
                    a.baro_altitude,
                    a.velocity,
                    a.true_track,
                    f.registration,
                    f.aircraft_model,
                    f.operatoricao
                FROM aircraft_states a
                JOIN fleet_data f 
                    ON a.icao24 = f.icao24
                WHERE a.snapshot_id = (
                    %s
                );
                """

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(statement_time)
            id_, time = cur.fetchall()[0]
            cur.execute(statement_data, (id_,) )
            rows = cur.fetchall()

    cur.close()
    
    flights = []
    for r in rows:
        icao_airline = r[9] 
        airline_codes = {'UAE': 'Emirates', 'ETD': 'Etihad', 'QTR': 'Qatar' }
        if not r[2] or not r[3]: # lat long should not be null
            continue
        airline = airline_codes[icao_airline]
        flights.append({
            "id": r[0],
            "callsign": r[1],
            "lat": r[2],
            "lon": r[3],
            "altitude": r[4] if r[4] is not None else 0,
            "velocity": r[5] if r[5] is not None else 0,
            "heading": r[6],
            "reg": r[7],
            "model": r[8],
            "airline": airline
        })

    return {"time": time, "flights": flights}