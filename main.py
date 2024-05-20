from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import psycopg2
from psycopg2.extras import RealDictCursor

from typing import Union

from time import time
import calendar
import datetime
import pytz

from dotenv import load_dotenv
import os


load_dotenv('.env')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/incident/")
async def get_incidents(limit: int = 10000, offset: int = 0):
    res = await execute_and_fetch_all(f"""
        select 
            *
        from incident
        order by ts desc
        limit {limit}
        offset {offset}
    """)
    
    count_res = await execute_and_fetch_all(f"""
        select 
            count(*) as total_count
        from incident
    """)
    
    for r in res:
        r['created_at'] = calendar.timegm(r['created_at'].timetuple())
        r['modified_at'] = calendar.timegm(r['modified_at'].timetuple())
        r['ts'] = calendar.timegm(r['ts'].timetuple())
        
    count = 0
    
    if count_res and len(count_res) > 0:
        count = count_res[0].get('total_count', None)
    
    return {
        'data': res,
        'totalCount': count
    }


class IncidentPayload(BaseModel):
    is_red_traffic_light_detected: bool
    epoch: int = round(time() * 1000) # millisec
    road_frame_filename: Union[str, None] = None
    full_frame_filename: Union[str, None] = None


@app.post("/api/incident/")
async def report_incident(payload: IncidentPayload):
    ts = datetime.datetime.fromtimestamp(payload.epoch / 1000)
    ts.replace(tzinfo=pytz.utc)
    
    await execute_and_fetch_all(f"""
        insert into incident
            (ts, is_red_traffic_light_detected, road_frame_filename, full_frame_filename)
        values
            ('{ts}', {payload.is_red_traffic_light_detected}, '{payload.road_frame_filename}', '{payload.full_frame_filename}')
        returning *;
    """)
    
    return { 'status': 'ok' }


@app.get(
    "/image/{file_name}",
    responses = {
        200: {
            "content": {"image/webp": {}}
        }
    },
    response_class=FileResponse
)
async def get_image(file_name: str):
    storage = os.environ.get('STORAGE_PATH', None)
    
    if not storage:
        raise Exception(f'STORAGE_PATH env variable is missing {storage=}')
    
    return FileResponse(f'{storage}{file_name}')

# define static for web app builded files
app.mount("/", StaticFiles(directory="./static", html=True, check_dir=True), name="static")


async def execute_and_fetch_all(sql_query):
    res = []

    try:
        with psycopg2.connect(
            host=os.environ.get('DATABASE_HOST', None),
            port=os.environ.get('DATABASE_PORT', None),
            database=os.environ.get('DATABASE_NAME', None),
            user=os.environ.get('DATABASE_USER', None),
            password=os.environ.get('DATABASE_PASS', None)
        ) as conn:
            with  conn.cursor(cursor_factory=RealDictCursor) as cur:
                try:
                    cur.execute(sql_query)
                except Exception as err:
                    print('Error during SQl query execution: ', err)
                
                res = cur.fetchall()

                # commit the changes to the database
                conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)    
    finally:
        return res

