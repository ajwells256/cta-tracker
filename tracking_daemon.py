import sqlite3 as db
import time
import requests
import json
import curses
import os

dbname = "backend.db"
refreshRate = 30 # in seconds
baseurl = "http://www.ctabustracker.com/bustime/api/v2/"
debugLevel = 2
debugFileName = "debugLog.txt"
keyFileName = "apikey.txt"
key = open(keyFileName, "r").read(25) # key is 24 long

def formatRow(row):
    return f"{row[3]}\t{row[4]} ({row[2]})\t\t{row[7]} min ({row[6]})\n"

def log(string):
    debugFile.write(str(string) + "\n")

def getPredictions(connection):
    c = connection.cursor()
    c.execute("DELETE FROM predictions")
    c.execute("SELECT stopId FROM tracking")
    results = c.fetchall()
    predUrl = baseurl + "getpredictions/"
    for stopId in results:
        params = {"key":key,"format":"json","stpid":stopId}
        response = requests.get(predUrl, params)
        json = response.json()
        if(debugLevel > 0):
            log(json)
        if("error" in json["bustime-response"]):
            continue
        preds = json["bustime-response"]["prd"]
        for pred in preds:
            _, _, _, curTime = parseTimeStamp(pred['tmstmp'])
            _, _, _, arrTime = parseTimeStamp(pred['prdtm'])
            waitTime = "0" if pred['prdctdn'] == "DUE" else pred['prdctdn']
            sql = f"INSERT INTO predictions VALUES (null, {pred['stpid']}, '{pred['stpnm']}', {pred['rt']}, '{pred['des']}', '{curTime}', '{arrTime}', {waitTime})"
            if(debugLevel > 1):
                log(sql)
            c.execute(sql)

def parseTimeStamp(ts):
    dt, tm = ts.split(" ")
    year = dt[0:4]
    month = dt[4:6]
    day = dt[6:]
    return (year, month, day, tm)

def displayPredictions(connection):
    predscr.clear()
    c = connection.cursor()
    c.execute("SELECT * FROM predictions ORDER BY predWait")
    results = c.fetchall()
    for row in results:
        if(debugLevel > 1):
            log(row)
        predscr.addstr(formatRow(row))
    predscr.refresh()

def getDbConnection():
    return db.connect(dbname)

def checkDb():
    if(not os.path.exists(dbname)):
        con = db.connect(dbname)
        cur = con.cursor()
        sql = "CREATE TABLE tracking(Id integer primary key, stopId integer)"
        cur.execute(sql)
        sql = ("CREATE TABLE predictions(Id integer primary key, "
            + "stopId integer, stopName varchar(100), routeNum integer, "
            + "routeDest varchar(100), curTime varchar(50), predTime varchar(50), "
            + "predWait integer)")
        cur.execute(sql)
        con.close()


def main():
    conn = getDbConnection()
    while(True):
        try:
            getPredictions(conn)
            displayPredictions(conn)
            time.sleep(refreshRate)
        except KeyboardInterrupt:
            conn.close()
            exit()
        except:
            conn.close()
            raise

def init():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    max_y, max_x = stdscr.getmaxyx()
    footer = stdscr.subwin(1, max_x, max_y-1, 0)
    footer.addstr("n = new stop")
    footer.refresh()
    predscr = stdscr.subwin(max_y-1, max_x, 0,0)
    return stdscr, footer, predscr

def teardown():
    curses.echo()
    curses.nocbreak
    curses.endwin()

if __name__ == "__main__":
    checkDb()
    try:
        stdscr, footer, predscr = init()
        if(debugLevel > 0):
            debugFile = open(debugFileName, "a")
            log(f"\nNew run! API key: {key}")
        main()
    finally:
        if(debugLevel > 0):
            debugFile.close()
        teardown()
