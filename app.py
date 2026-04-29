from flask import Flask, jsonify
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def fetch_yahoo(ticker, interval='1d', range_='3mo'):
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    # Fallback su query1
    try:
        url2 = url.replace('query2', 'query1')
        r = requests.get(url2, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

@app.route('/')
def home():
    return jsonify({'status': 'Trading Radar API online', 'version': '1.0'})

@app.route('/daily/<ticker>')
def daily(ticker):
    data = fetch_yahoo(ticker, interval='1d', range_='3mo')
    if not data or not data.get('chart', {}).get('result'):
        return jsonify({'error': 'No data'}), 404
    return jsonify(data)

@app.route('/intraday/<ticker>')
def intraday(ticker):
    data = fetch_yahoo(ticker, interval='15m', range_='2d')
    if not data or not data.get('chart', {}).get('result'):
        return jsonify({'error': 'No data'}), 404
    return jsonify(data)

@app.route('/scan')
def scan():
    """Scansione completa di tutti i titoli — restituisce dati pre-elaborati"""
    tickers = [
        # Mega cap
        'TSLA','NVDA','AMD','META','AMZN','GOOGL','MSFT','AAPL','NFLX','INTC','ARM','QCOM','NIO','BABA',
        # Growth
        'PLTR','CRWD','NET','SNOW','DDOG','MDB','RBLX','SOFI','UPST','AFRM','HOOD','LC','DKNG',
        'ROKU','ZM','LYFT','UBER','DASH','PATH','SMCI','FUTU','OPEN','RIVN','SPCE',
        'ASTS','RKLB','JOBY','ACHR','LUNR','SOUN','IONQ',
        # Biotech
        'MRNA','NVAX','BNTX','CRSP','BEAM','EDIT','NTLA','RXRX','ARWR','EXEL','FOLD','FATE','RARE',
        # Crypto-equity
        'COIN','MSTR','RIOT','MARA','CLSK','HUT','CIFR','WULF','IREN',
        # Energia
        'PLUG','FCEL','BE','ENPH','SEDG','RUN','NOVA',
        # Meme
        'GME','AMC','NKLA','GOEV',
        # Crypto
        'BTC-USD','ETH-USD','SOL-USD','XRP-USD','ADA-USD','DOGE-USD','LINK-USD','AVAX-USD','DOT-USD'
    ]

    results = []
    for ticker in tickers:
        try:
            # Daily
            d_data = fetch_yahoo(ticker, '1d', '3mo')
            if not d_data or not d_data.get('chart', {}).get('result'):
                continue
            dr = d_data['chart']['result'][0]
            dq = dr['indicators']['quote'][0]
            closes = [p for p in (dq.get('close') or []) if p is not None]
            highs  = [p for p in (dq.get('high')  or []) if p is not None]
            lows   = [p for p in (dq.get('low')   or []) if p is not None]
            vols   = [p for p in (dq.get('volume') or []) if p is not None]
            if len(closes) < 15:
                continue

            # Intraday
            i_closes, i_highs, i_lows, i_vols = [], [], [], []
            i_data = fetch_yahoo(ticker, '15m', '2d')
            if i_data and i_data.get('chart', {}).get('result'):
                ir = i_data['chart']['result'][0]
                iq = ir['indicators']['quote'][0]
                ic = iq.get('close') or []
                ih = iq.get('high')  or []
                il = iq.get('low')   or []
                iv = iq.get('volume') or []
                valid = [i for i, v in enumerate(ic) if v is not None]
                last26 = valid[-26:]
                i_closes = [ic[i] for i in last26]
                i_highs  = [ih[i] if ih[i] else ic[i] for i in last26]
                i_lows   = [il[i] if il[i] else ic[i] for i in last26]
                i_vols   = [iv[i] or 0 for i in last26]

            results.append({
                'ticker': ticker,
                'daily': {
                    'closes': closes[-30:],
                    'highs': highs[-30:],
                    'lows': lows[-30:],
                    'vols': vols[-30:]
                },
                'intraday': {
                    'closes': i_closes,
                    'highs': i_highs,
                    'lows': i_lows,
                    'vols': i_vols
                } if i_closes else None
            })

            time.sleep(0.15)  # gentile con Yahoo Finance

        except Exception as e:
            continue

    return jsonify({'results': results, 'count': len(results)})

if __name__ == '__main__':
    app.run(debug=False)
